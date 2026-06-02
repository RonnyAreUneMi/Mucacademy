/**
 * Resumen IA del evento (Betto) — pantalla mobile completa.
 *
 * Estados del payload:
 *   - 'no_existe' / 'pendiente' / 'buscando' / 'procesando'
 *     / 'sin_transcript' / 'fallido' / 'listo'
 *
 * Cuando está LISTO muestra:
 *   - Banner ámbar si no asistió
 *   - Card grabación (link Drive)
 *   - Resumen Markdown
 *   - Puntos clave (numerados)
 *   - Próximos pasos (checks)
 *   - CTA al cuestionario / resultados de intentos previos
 */
import { useEffect, useState, useCallback } from 'react';
import {
  Linking, Pressable, ScrollView, StyleSheet, Text, View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';
import * as SecureStore from 'expo-secure-store';

import { api, APIError } from '@/api/client';
import {
  brandScale, colors, radius, shadows, spacing, themed, typography,
} from '@/theme/tokens';
import { useTheme } from '@/stores/theme';
import { BettoLogo, Button, Loader, NeuCard, useToast } from '@/components/ui';

type Status =
  | 'no_existe' | 'pending' | 'searching' | 'processing'
  | 'ready' | 'no_transcript' | 'failed';

type Question = {
  question: string;
  options: string[];
  correct_idx: number;
  explanation?: string;
};

type Attempt = {
  id: number;
  correct: number;
  total: number;
  porcentaje: number;
  total_time_seconds: number;
  created_at: string;
};

type Recording = { file_id: string; name: string; web_link: string };

type SummaryPayload = {
  // Cuando hay resumen el backend emite `status`; cuando no existe, `estado: 'no_existe'`.
  status?: Status;
  estado?: Status;
  estado_display?: string;
  is_ready?: boolean;
  has_failed?: boolean;
  message?: string;
  summary_md?: string;
  key_points?: string[];
  next_steps?: string[];
  quiz?: Question[];
  duration_minutes?: number;
  ai_model?: string;
  processed_at?: string | null;
  transcripcion_habilitada?: boolean;

  // Enriquecido cuando viene auth de participante
  intentos?: Attempt[];
  mejor_intento?: Attempt | null;
  intentos_disponibles?: number;
  max_intentos?: number;
  recording?: Recording | null;
  asistio?: boolean;
  inscrito?: boolean;
};

const POLL_INTERVAL_MS = 8000;
const PROCESSING_STATES: Status[] = ['pending', 'searching', 'processing'];

/** El estado efectivo: `status` (resumen existente) o `estado` (sentinela no_existe). */
function effectiveStatus(d: SummaryPayload): Status {
  return d.status ?? d.estado ?? 'no_existe';
}

export default function ResumenScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const theme = useTheme();
  const t = themed(theme);
  const toast = useToast();

  const [data, setData] = useState<SummaryPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await api.get<SummaryPayload>(`/api/v1/public/sessions/${id}/resumen/`);
      setData(res);
    } catch (e: any) {
      toast.error(e?.message ?? 'No pudimos cargar el resumen.', 'Error');
    } finally {
      setLoading(false);
    }
  }, [id, toast]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!data || !PROCESSING_STATES.includes(effectiveStatus(data))) return;
    const handle = setInterval(load, POLL_INTERVAL_MS);
    return () => clearInterval(handle);
  }, [data, load]);

  async function trigger() {
    setTriggering(true);
    try {
      await api.post(`/api/v1/public/sessions/${id}/resumen/procesar/`);
      toast.info('Procesamiento iniciado. Esto puede tardar unos minutos.', 'Encolado');
      await load();
    } catch (e: any) {
      const msg = e instanceof APIError ? (e.data?.error ?? e.message) : (e?.message ?? 'Error');
      toast.error(msg, 'No pudimos iniciar');
    } finally {
      setTriggering(false);
    }
  }

  if (loading || !data) {
    return (
      <View style={[styles.safe, { backgroundColor: t.bg, alignItems: 'center', justifyContent: 'center' }]}>
        <Loader size={88} />
      </View>
    );
  }

  return (
    <View style={[styles.safe, { backgroundColor: t.bg }]}>
      <ScrollView
        contentContainerStyle={{
          paddingTop: insets.top + spacing.base,
          paddingBottom: insets.bottom + spacing.xxl,
        }}
        showsVerticalScrollIndicator={false}
      >
        {/* Back */}
        <View style={styles.headerRow}>
          <Pressable
            onPress={() => router.back()}
            style={({ pressed }) => [
              styles.backBtn,
              { backgroundColor: t.cardSoft, borderColor: t.border },
              pressed && { opacity: 0.7 },
            ]}
            hitSlop={10}
          >
            <Ionicons name="chevron-back" size={20} color={t.text} />
          </Pressable>
          <Text style={[styles.backText, { color: t.textMuted }]}>Volver</Text>
        </View>

        {/* Hero limpio (sin fondo masivo) */}
        <View style={styles.hero}>
          <View style={styles.heroAvatarWrap}>
            <BettoLogo size={64} />
            <View style={styles.heroBadge}>
              <Ionicons name="sparkles" size={12} color="#FFFFFF" />
            </View>
          </View>
          <View style={{ flex: 1, minWidth: 0 }}>
            <Text style={styles.heroEyebrow}>RESUMEN DE BETTO</Text>
            <Text style={[styles.heroTitle, { color: t.text }]} numberOfLines={2}>
              {/* Lo dejamos en blanco si no hay datos; el resumen NO trae el título */}
              Resumen del evento
            </Text>
            {data.duration_minutes ? (
              <Text style={[styles.heroMeta, { color: t.textMuted }]}>
                <Ionicons name="time" size={11} color={colors.brand} />{' '}
                {data.duration_minutes} min de transcript
              </Text>
            ) : null}
          </View>
        </View>

        {/* Cuerpo según estado */}
        {effectiveStatus(data) === 'ready' ? (
          <ListoView data={data} sesionId={String(id)} />
        ) : PROCESSING_STATES.includes(effectiveStatus(data)) ? (
          <ProcessingView estado={effectiveStatus(data)} />
        ) : effectiveStatus(data) === 'no_transcript' ? (
          <SinTranscriptView triggering={triggering} onRetry={trigger} />
        ) : effectiveStatus(data) === 'failed' ? (
          <FallidoView triggering={triggering} onRetry={trigger} />
        ) : (
          <NoExisteView triggering={triggering} onTrigger={trigger} />
        )}
      </ScrollView>
    </View>
  );
}

// ── Vistas por estado ────────────────────────────────────────────

function NoExisteView({ triggering, onTrigger }: { triggering: boolean; onTrigger: () => void }) {
  const t = themed(useTheme());
  return (
    <View style={styles.section}>
      <NeuCard style={styles.stateCard}>
        <View style={[styles.iconBubble, { backgroundColor: 'rgba(245,136,48,0.14)' }]}>
          <Ionicons name="sparkles" size={28} color={colors.brand} />
        </View>
        <Text style={[styles.stateTitle, { color: t.text }]}>Aún no se generó el resumen</Text>
        <Text style={[styles.stateBody, { color: t.textMuted }]}>
          Podés iniciar el procesamiento ahora. Betto buscará el transcript y generará el resumen + cuestionario.
        </Text>
        <Button
          tone="brand" variant="filled" size="lg" fullWidth
          loading={triggering} onPress={onTrigger}
          iconLeft={!triggering ? <Ionicons name="sparkles" size={16} color="#FFFFFF" /> : undefined}
        >
          Generar resumen con IA
        </Button>
      </NeuCard>
    </View>
  );
}

function ProcessingView({ estado }: { estado: Status }) {
  const t = themed(useTheme());
  const labels: Record<string, { eyebrow: string; title: string; body: string }> = {
    pending:    { eyebrow: 'EN COLA', title: 'Encolado para procesar', body: 'En segundos comenzaremos.' },
    searching:  { eyebrow: 'BUSCANDO', title: 'Buscando el transcript', body: 'Estamos revisando Google Drive.' },
    processing: { eyebrow: 'IA TRABAJANDO', title: 'Betto está pensando…', body: 'Generando resumen + cuestionario. Esto toma 30-90 segundos.' },
  };
  const lbl = labels[estado] ?? labels.processing;
  return (
    <View style={styles.section}>
      <NeuCard style={styles.stateCard}>
        <Loader size={88} />
        <Text style={[styles.stateEyebrow, { color: colors.info }]}>{lbl.eyebrow}</Text>
        <Text style={[styles.stateTitle, { color: t.text }]}>{lbl.title}</Text>
        <Text style={[styles.stateBody, { color: t.textMuted }]}>
          {lbl.body}
          {'\n\n'}Esta pantalla se actualiza sola.
        </Text>
      </NeuCard>
    </View>
  );
}

function SinTranscriptView({ triggering, onRetry }: { triggering: boolean; onRetry: () => void }) {
  const t = themed(useTheme());
  return (
    <View style={styles.section}>
      <NeuCard style={styles.stateCard}>
        <View style={[styles.iconBubble, { backgroundColor: 'rgba(245,158,11,0.14)' }]}>
          <Ionicons name="time" size={28} color={colors.warning} />
        </View>
        <Text style={[styles.stateTitle, { color: t.text }]}>El transcript todavía no está</Text>
        <Text style={[styles.stateBody, { color: t.textMuted }]}>
          Google Meet tarda 5–30 minutos en publicar el transcript. Probá de nuevo en un rato.
        </Text>
        <Button
          tone="brand" variant="outline" size="lg" fullWidth
          loading={triggering} onPress={onRetry}
          iconLeft={!triggering ? <Ionicons name="refresh" size={16} color={colors.brand} /> : undefined}
        >
          Reintentar
        </Button>
      </NeuCard>
    </View>
  );
}

function FallidoView({ triggering, onRetry }: { triggering: boolean; onRetry: () => void }) {
  const t = themed(useTheme());
  return (
    <View style={styles.section}>
      <NeuCard style={styles.stateCard}>
        <View style={[styles.iconBubble, { backgroundColor: 'rgba(239,68,68,0.14)' }]}>
          <Ionicons name="alert-circle" size={28} color={colors.danger} />
        </View>
        <Text style={[styles.stateTitle, { color: t.text }]}>Algo no salió bien</Text>
        <Text style={[styles.stateBody, { color: t.textMuted }]}>
          Hubo un problema procesando el transcript. Podemos volver a intentarlo.
        </Text>
        <Button
          tone="brand" variant="filled" size="lg" fullWidth
          loading={triggering} onPress={onRetry}
          iconLeft={!triggering ? <Ionicons name="refresh" size={16} color="#FFFFFF" /> : undefined}
        >
          Reintentar
        </Button>
      </NeuCard>
    </View>
  );
}

function ListoView({ data, sesionId }: { data: SummaryPayload; sesionId: string }) {
  const t = themed(useTheme());
  const toast = useToast();
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  /**
   * Descarga el PDF al cache local del dispositivo y abre el share sheet
   * nativo (guardar en Drive, mandar por WhatsApp, imprimir, etc.).
   */
  async function descargarPdf() {
    if (downloadingPdf) return;
    setDownloadingPdf(true);
    try {
      const token = await SecureStore.getItemAsync('certifai.token');
      if (!token) {
        toast.error('Sesión expirada. Volvé a iniciar sesión.', 'Auth');
        return;
      }

      const url = `${api.baseUrl}/api/v1/public/sessions/${sesionId}/resumen/pdf/`;
      const filename = `Resumen-Betto-sesion-${sesionId}.pdf`;
      // Cache directory en SDK 54+: usa la nueva API File (no documentDirectory legacy)
      const dest = `${FileSystem.Paths.cache.uri}${filename}`;

      const result = await FileSystem.downloadAsync(url, dest, {
        headers: { Authorization: `Token ${token}` },
      });

      if (result.status !== 200) {
        toast.error(`Error ${result.status} descargando el PDF.`, 'Descarga');
        return;
      }

      const canShare = await Sharing.isAvailableAsync();
      if (canShare) {
        await Sharing.shareAsync(result.uri, {
          mimeType: 'application/pdf',
          dialogTitle: 'Compartir resumen de Betto',
          UTI: 'com.adobe.pdf',
        });
      } else {
        toast.success('PDF guardado en el dispositivo.', 'Listo');
      }
    } catch (e: any) {
      toast.error(e?.message ?? 'No se pudo descargar.', 'Error');
    } finally {
      setDownloadingPdf(false);
    }
  }

  return (
    <View>
      {/* Banner ausencia */}
      {data.asistio === false ? (
        <View style={styles.section}>
          <View style={[styles.banner, { backgroundColor: 'rgba(245,158,11,0.10)', borderColor: 'rgba(245,158,11,0.30)' }]}>
            <View style={[styles.bannerIcon, { backgroundColor: 'rgba(245,158,11,0.18)' }]}>
              <Ionicons name="information-circle" size={18} color={colors.warning} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={[styles.bannerTitle, { color: t.text }]}>No registramos tu asistencia</Text>
              <Text style={[styles.bannerBody, { color: t.textMuted }]}>
                Igual te dejamos el resumen y la grabación para que te pongas al día.
              </Text>
            </View>
          </View>
        </View>
      ) : null}

      {/* Grabación de Meet */}
      {data.recording ? (
        <View style={styles.section}>
          <Pressable
            onPress={() => Linking.openURL(data.recording!.web_link)}
            style={({ pressed }) => [pressed && { transform: [{ scale: 0.98 }], opacity: 0.95 }]}
          >
            <LinearGradient
              colors={['#3B82F6', '#1E40AF', '#0F1F4D']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
              style={styles.recordingCard}
            >
              <Ionicons
                name="videocam" size={140} color="rgba(255,255,255,0.10)"
                style={styles.recordingDecor}
              />
              <View style={styles.recordingHead}>
                <View style={styles.recordingIconWrap}>
                  <Ionicons name="play-circle" size={28} color="#FFFFFF" />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.recordingEyebrow}>GRABACIÓN · MEET</Text>
                  <Text style={styles.recordingTitle}>Ver el video del evento</Text>
                </View>
                <View style={styles.recordingArrow}>
                  <Ionicons name="open-outline" size={18} color="#FFFFFF" />
                </View>
              </View>
              <Text style={styles.recordingFile} numberOfLines={2}>{data.recording.name}</Text>
            </LinearGradient>
          </Pressable>
        </View>
      ) : null}

      {/* Descargar PDF del resumen (nativo) */}
      <View style={styles.section}>
        <Pressable
          onPress={descargarPdf}
          disabled={downloadingPdf}
          style={({ pressed }) => [
            pressed && !downloadingPdf && { transform: [{ scale: 0.98 }], opacity: 0.95 },
            downloadingPdf && { opacity: 0.7 },
          ]}
        >
          <LinearGradient
            colors={[brandScale[500], '#E8721C', brandScale[700]]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.recordingCard}
          >
            <Ionicons
              name="document-text" size={140} color="rgba(255,255,255,0.12)"
              style={styles.recordingDecor}
            />
            <View style={styles.recordingHead}>
              <View style={styles.recordingIconWrap}>
                <Ionicons
                  name={downloadingPdf ? 'hourglass' : 'download'}
                  size={28}
                  color="#FFFFFF"
                />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.recordingEyebrow}>
                  {downloadingPdf ? 'GENERANDO PDF…' : 'DESCARGAR PDF'}
                </Text>
                <Text style={styles.recordingTitle}>
                  {downloadingPdf ? 'Un momento' : 'Resumen offline'}
                </Text>
              </View>
              <View style={styles.recordingArrow}>
                <Ionicons name="share-outline" size={18} color="#FFFFFF" />
              </View>
            </View>
            <Text style={styles.recordingFile} numberOfLines={2}>
              {downloadingPdf
                ? 'Preparando archivo para compartir o guardar…'
                : 'Compartí, guardá en Drive o imprimí · sin salir de la app'}
            </Text>
          </LinearGradient>
        </Pressable>
      </View>

      {/* Resumen ejecutivo */}
      {data.summary_md ? (
        <View style={styles.section}>
          <View style={styles.sectionHead}>
            <View style={[styles.sectionEyebrowIcon, { backgroundColor: 'rgba(245,136,48,0.14)' }]}>
              <Ionicons name="document-text" size={13} color={colors.brand} />
            </View>
            <Text style={[styles.sectionEyebrow, { color: colors.brand }]}>RESUMEN EJECUTIVO</Text>
          </View>
          <Text style={[styles.sectionTitle, { color: t.text }]}>De qué se habló</Text>
          <NeuCard style={{ marginTop: spacing.base }}>
            <MarkdownText source={data.summary_md} />
          </NeuCard>
        </View>
      ) : null}

      {/* Puntos clave */}
      {data.key_points && data.key_points.length > 0 ? (
        <View style={styles.section}>
          <View style={styles.sectionHead}>
            <View style={[styles.sectionEyebrowIcon, { backgroundColor: 'rgba(245,136,48,0.14)' }]}>
              <Ionicons name="ribbon" size={13} color={colors.brand} />
            </View>
            <Text style={[styles.sectionEyebrow, { color: colors.brand }]}>HALLAZGOS</Text>
          </View>
          <Text style={[styles.sectionTitle, { color: t.text }]}>Puntos clave</Text>
          <View style={{ gap: spacing.sm, marginTop: spacing.base }}>
            {data.key_points.map((p, i) => (
              <View key={i} style={[styles.bulletCard, { backgroundColor: t.cardSoft, borderColor: t.border }]}>
                <View style={styles.bulletNum}>
                  <Text style={styles.bulletNumText}>{i + 1}</Text>
                </View>
                <Text style={[styles.bulletText, { color: t.text }]}>{p}</Text>
              </View>
            ))}
          </View>
        </View>
      ) : null}

      {/* Próximos pasos */}
      {data.next_steps && data.next_steps.length > 0 ? (
        <View style={styles.section}>
          <View style={styles.sectionHead}>
            <View style={[styles.sectionEyebrowIcon, { backgroundColor: 'rgba(16,185,129,0.14)' }]}>
              <Ionicons name="checkmark-done" size={13} color={colors.success} />
            </View>
            <Text style={[styles.sectionEyebrow, { color: colors.success }]}>ACCIONES</Text>
          </View>
          <Text style={[styles.sectionTitle, { color: t.text }]}>Próximos pasos</Text>
          <View style={{ gap: spacing.sm, marginTop: spacing.base }}>
            {data.next_steps.map((p, i) => (
              <View key={i} style={[styles.actionCard, { backgroundColor: t.cardSoft, borderColor: t.border }]}>
                <View style={[styles.actionIcon, { backgroundColor: 'rgba(16,185,129,0.14)' }]}>
                  <Ionicons name="arrow-forward" size={14} color={colors.success} />
                </View>
                <Text style={[styles.bulletText, { color: t.text }]}>{p}</Text>
              </View>
            ))}
          </View>
        </View>
      ) : null}

      {/* Cuestionario: CTA o resultados previos */}
      {data.quiz && data.quiz.length > 0 ? (
        <View style={styles.section}>
          <CuestionarioBlock data={data} sesionId={sesionId} />
        </View>
      ) : null}

      {/* Footer info IA */}
      <View style={[styles.section, { alignItems: 'center', marginTop: spacing.lg }]}>
        <Text style={[styles.footerInfo, { color: t.textMuted }]}>
          <Ionicons name="hardware-chip-outline" size={11} color={t.textMuted} />{' '}
          Generado con IA · {data.ai_model}
        </Text>
      </View>
    </View>
  );
}

// ── Bloque del cuestionario (CTA o resultados previos) ────────────

function CuestionarioBlock({ data, sesionId }: { data: SummaryPayload; sesionId: string }) {
  const t = themed(useTheme());
  const intentos = data.intentos ?? [];
  const disponibles = data.intentos_disponibles ?? 2;
  const maxInt = data.max_intentos ?? 2;

  function goToQuiz() {
    router.push(`/event/cuestionario/${sesionId}`);
  }

  // Ya hay intentos previos: mostrar tarjeta de resultados
  if (intentos.length > 0) {
    return (
      <View>
        <LinearGradient
          colors={['#1E1B4B', '#312E81', '#4C1D95']}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.quizResultsCard}
        >
          <Ionicons name="trophy" size={140} color="rgba(255,255,255,0.06)" style={styles.recordingDecor} />

          <View style={styles.recordingHead}>
            <View style={[styles.recordingIconWrap, { backgroundColor: 'rgba(245,158,11,0.30)' }]}>
              <Ionicons name="trophy" size={22} color="#FBBF24" />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.recordingEyebrow}>TUS RESULTADOS</Text>
              <Text style={styles.recordingTitle}>Cuestionario · Repaso</Text>
            </View>
          </View>

          <Text style={styles.quizMeta}>
            {intentos.length} de {maxInt} intentos usados
            {data.mejor_intento ? `  ·  Mejor: ${data.mejor_intento.correct}/${data.mejor_intento.total} (${data.mejor_intento.porcentaje}%)` : ''}
          </Text>

          <View style={{ gap: 8, marginTop: spacing.base }}>
            {intentos.map((it, i) => (
              <View key={it.id} style={styles.intentoRow}>
                <View style={styles.intentoNum}>
                  <Text style={styles.intentoNumText}>#{i + 1}</Text>
                </View>
                <View style={{ flex: 1, minWidth: 0 }}>
                  <Text style={styles.intentoMain}>
                    {it.correct}/{it.total} correctas · {it.porcentaje}%
                  </Text>
                  <Text style={styles.intentoMeta}>
                    <Ionicons name="time-outline" size={10} color="rgba(255,255,255,0.65)" />{' '}
                    {it.total_time_seconds}s
                  </Text>
                </View>
                <View style={styles.intentoBar}>
                  <View
                    style={[
                      styles.intentoBarFill,
                      {
                        width: `${it.porcentaje}%`,
                        backgroundColor:
                          it.porcentaje >= 80 ? '#10B981'
                          : it.porcentaje >= 50 ? '#F59E0B'
                          : '#EF4444',
                      },
                    ]}
                  />
                </View>
              </View>
            ))}
          </View>

          {disponibles > 0 ? (
            <Pressable
              onPress={goToQuiz}
              style={({ pressed }) => [styles.quizRetryBtn, pressed && { opacity: 0.85 }]}
            >
              <LinearGradient
                colors={[brandScale[500], brandScale[700]]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={styles.quizRetryGrad}
              >
                <Ionicons name="refresh" size={16} color="#FFFFFF" />
                <Text style={styles.quizRetryText}>
                  Volver a intentar ({disponibles} restante{disponibles === 1 ? '' : 's'})
                </Text>
              </LinearGradient>
            </Pressable>
          ) : (
            <View style={styles.quizDoneTag}>
              <Ionicons name="flag" size={12} color="rgba(255,255,255,0.85)" />
              <Text style={styles.quizDoneText}>Completaste tus {maxInt} intentos</Text>
            </View>
          )}
        </LinearGradient>
      </View>
    );
  }

  // Sin intentos: CTA para empezar
  return (
    <Pressable
      onPress={goToQuiz}
      style={({ pressed }) => [pressed && { transform: [{ scale: 0.98 }], opacity: 0.95 }]}
    >
      <LinearGradient
        colors={['#6D28D9', '#7C3AED', '#A855F7']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.quizCtaCard}
      >
        <Ionicons name="school" size={140} color="rgba(255,255,255,0.10)" style={styles.recordingDecor} />
        <View style={styles.recordingHead}>
          <View style={[styles.recordingIconWrap, { backgroundColor: 'rgba(255,255,255,0.18)' }]}>
            <Ionicons name="school" size={26} color="#FFFFFF" />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.recordingEyebrow}>REPASO INTERACTIVO</Text>
            <Text style={styles.recordingTitle}>Probá lo que aprendiste</Text>
          </View>
          <View style={styles.recordingArrow}>
            <Ionicons name="arrow-forward" size={18} color="#FFFFFF" />
          </View>
        </View>
        <Text style={styles.recordingFile}>
          {data.quiz?.length} preguntas · 30 seg c/u · {maxInt} intentos
        </Text>
        <View style={[styles.quizCtaPill]}>
          <Ionicons name="flash" size={11} color="#FFFFFF" />
          <Text style={styles.quizCtaPillText}>Empezar</Text>
        </View>
      </LinearGradient>
    </Pressable>
  );
}

// ── Markdown nativo (mínimo: # ## ### **bold** *ital* - bullets) ─

function MarkdownText({ source }: { source: string }) {
  const t = themed(useTheme());
  const lines = source.split(/\r?\n/);
  const blocks: React.ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();
    if (!trimmed) { i++; continue; }

    const h3 = trimmed.match(/^###\s+(.+)$/);
    if (h3) { blocks.push(<Text key={key++} style={[styles.mdH3, { color: t.text }]}>{h3[1]}</Text>); i++; continue; }
    const h2 = trimmed.match(/^##\s+(.+)$/);
    if (h2) { blocks.push(<Text key={key++} style={[styles.mdH2, { color: t.text }]}>{h2[1]}</Text>); i++; continue; }
    const h1 = trimmed.match(/^#\s+(.+)$/);
    if (h1) { blocks.push(<Text key={key++} style={[styles.mdH1, { color: t.text }]}>{h1[1]}</Text>); i++; continue; }

    if (/^[-*]\s+/.test(trimmed) || /^\d+\.\s+/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length) {
        const m = lines[i].trim().match(/^(?:[-*]|\d+\.)\s+(.+)$/);
        if (!m) break;
        items.push(m[1]);
        i++;
      }
      blocks.push(
        <View key={key++} style={styles.mdList}>
          {items.map((it, idx) => (
            <View key={idx} style={styles.mdLi}>
              <Text style={[styles.mdLiBullet, { color: colors.brand }]}>•</Text>
              <Text style={[styles.mdLiText, { color: t.textMuted }]}>{renderInline(it, t.text)}</Text>
            </View>
          ))}
        </View>
      );
      continue;
    }

    const paraLines = [line];
    i++;
    while (i < lines.length) {
      const next = lines[i].trim();
      if (!next) break;
      if (/^#{1,3}\s+/.test(next)) break;
      if (/^[-*]\s+/.test(next) || /^\d+\.\s+/.test(next)) break;
      paraLines.push(lines[i]);
      i++;
    }
    blocks.push(
      <Text key={key++} style={[styles.mdP, { color: t.textMuted }]}>
        {renderInline(paraLines.join(' '), t.text)}
      </Text>
    );
  }

  return <View style={{ gap: 4 }}>{blocks}</View>;
}

function renderInline(text: string, strongColor: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  const re = /(\*\*([^*]+)\*\*|\*([^*]+)\*)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    if (m[2] !== undefined) parts.push(<Text key={key++} style={{ color: strongColor, fontWeight: typography.black }}>{m[2]}</Text>);
    else if (m[3] !== undefined) parts.push(<Text key={key++} style={{ fontStyle: 'italic' }}>{m[3]}</Text>);
    last = re.lastIndex;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

// ── Estilos ──────────────────────────────────────────────────────

const styles = StyleSheet.create({
  safe: { flex: 1 },

  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingHorizontal: spacing.xl,
    marginBottom: spacing.base,
  },
  backBtn: {
    width: 38, height: 38,
    borderRadius: radius.full,
    borderWidth: 1,
    alignItems: 'center', justifyContent: 'center',
  },
  backText: {
    fontSize: typography.sm,
    fontWeight: typography.bold,
  },

  hero: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingHorizontal: spacing.xl,
    marginBottom: spacing.lg,
  },
  heroAvatarWrap: { position: 'relative' },
  heroBadge: {
    position: 'absolute',
    bottom: -2, right: -2,
    width: 22, height: 22,
    borderRadius: 11,
    backgroundColor: colors.brand,
    alignItems: 'center', justifyContent: 'center',
    borderWidth: 2, borderColor: '#FFFFFF',
  },
  heroEyebrow: {
    fontSize: typography.xs - 1,
    fontWeight: typography.black,
    letterSpacing: 1.8,
    color: colors.brand,
  },
  heroTitle: {
    fontSize: typography.xxl,
    fontWeight: typography.black,
    letterSpacing: -0.4,
    marginTop: 2,
  },
  heroMeta: {
    fontSize: typography.xs,
    fontWeight: typography.medium,
    marginTop: 4,
  },

  section: {
    paddingHorizontal: spacing.xl,
    marginTop: spacing.lg,
  },

  // Estado cards
  stateCard: {
    alignItems: 'center',
    gap: spacing.base,
    paddingVertical: spacing.lg,
  },
  iconBubble: {
    width: 56, height: 56,
    borderRadius: radius.full,
    alignItems: 'center', justifyContent: 'center',
  },
  stateEyebrow: {
    fontSize: typography.xs,
    fontWeight: typography.black,
    letterSpacing: 1.4,
  },
  stateTitle: {
    fontSize: typography.xl,
    fontWeight: typography.black,
    letterSpacing: -0.3,
    textAlign: 'center',
  },
  stateBody: {
    fontSize: typography.sm,
    fontWeight: typography.medium,
    textAlign: 'center',
    lineHeight: typography.sm * 1.5,
    paddingHorizontal: spacing.sm,
  },

  // Banner ausencia
  banner: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
    padding: spacing.base,
    borderRadius: radius.lg,
    borderWidth: 1,
  },
  bannerIcon: {
    width: 32, height: 32,
    borderRadius: radius.full,
    alignItems: 'center', justifyContent: 'center',
  },
  bannerTitle: {
    fontSize: typography.sm,
    fontWeight: typography.black,
  },
  bannerBody: {
    fontSize: typography.xs,
    fontWeight: typography.medium,
    marginTop: 2,
    lineHeight: typography.xs * 1.5,
  },

  // Card grabación
  recordingCard: {
    borderRadius: radius.xl,
    padding: spacing.base,
    overflow: 'hidden',
    position: 'relative',
    ...shadows.lg,
  },
  recordingDecor: {
    position: 'absolute',
    right: -20, bottom: -20,
  },
  recordingHead: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  recordingIconWrap: {
    width: 48, height: 48,
    borderRadius: radius.lg,
    backgroundColor: 'rgba(255,255,255,0.15)',
    alignItems: 'center', justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.30)',
  },
  recordingEyebrow: {
    fontSize: typography.xs - 1,
    fontWeight: typography.black,
    letterSpacing: 1.6,
    color: 'rgba(255,255,255,0.85)',
  },
  recordingTitle: {
    color: '#FFFFFF',
    fontSize: typography.lg,
    fontWeight: typography.black,
    letterSpacing: -0.3,
    marginTop: 2,
  },
  recordingArrow: {
    width: 36, height: 36,
    borderRadius: radius.full,
    backgroundColor: 'rgba(255,255,255,0.15)',
    alignItems: 'center', justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.30)',
  },
  recordingFile: {
    color: 'rgba(255,255,255,0.85)',
    fontSize: typography.xs,
    fontWeight: typography.medium,
    marginTop: spacing.sm,
  },

  // Sección headers
  sectionHead: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  sectionEyebrowIcon: {
    width: 22, height: 22,
    borderRadius: radius.sm,
    alignItems: 'center', justifyContent: 'center',
  },
  sectionEyebrow: {
    fontSize: typography.xs,
    fontWeight: typography.black,
    letterSpacing: 1.4,
  },
  sectionTitle: {
    fontSize: typography.xl,
    fontWeight: typography.black,
    letterSpacing: -0.3,
    marginTop: spacing.xs,
  },

  // Bullet/action cards
  bulletCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
    padding: spacing.base,
    borderRadius: radius.lg,
    borderWidth: 1,
  },
  bulletNum: {
    width: 26, height: 26,
    borderRadius: radius.full,
    backgroundColor: brandScale[500],
    alignItems: 'center', justifyContent: 'center',
    ...shadows.brand,
  },
  bulletNumText: {
    color: '#FFFFFF',
    fontSize: typography.xs,
    fontWeight: typography.black,
  },
  bulletText: {
    flex: 1,
    fontSize: typography.sm,
    fontWeight: typography.medium,
    lineHeight: typography.sm * 1.45,
  },
  actionCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
    padding: spacing.base,
    borderRadius: radius.lg,
    borderWidth: 1,
  },
  actionIcon: {
    width: 26, height: 26,
    borderRadius: radius.full,
    alignItems: 'center', justifyContent: 'center',
  },

  // Markdown
  mdH1: { fontSize: typography.lg, fontWeight: typography.black, letterSpacing: -0.3, marginTop: spacing.sm, marginBottom: 4 },
  mdH2: { fontSize: typography.md, fontWeight: typography.black, letterSpacing: -0.2, marginTop: spacing.sm, marginBottom: 2 },
  mdH3: { fontSize: typography.base, fontWeight: typography.black, letterSpacing: -0.15, marginTop: spacing.xs, marginBottom: 2 },
  mdP:  { fontSize: typography.sm, fontWeight: typography.regular, lineHeight: typography.sm * 1.55, marginVertical: 4 },
  mdList: { marginVertical: 6, gap: 4 },
  mdLi: { flexDirection: 'row', alignItems: 'flex-start', gap: 6, paddingLeft: 4 },
  mdLiBullet: { fontSize: typography.base, lineHeight: typography.sm * 1.55, fontWeight: typography.black },
  mdLiText: { flex: 1, fontSize: typography.sm, fontWeight: typography.regular, lineHeight: typography.sm * 1.55 },

  // Quiz CTA / resultados
  quizCtaCard: {
    borderRadius: radius.xl,
    padding: spacing.base,
    overflow: 'hidden',
    position: 'relative',
    ...shadows.lg,
  },
  quizCtaPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    alignSelf: 'flex-start',
    paddingHorizontal: spacing.sm,
    paddingVertical: 6,
    borderRadius: radius.full,
    backgroundColor: 'rgba(255,255,255,0.18)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.30)',
    marginTop: spacing.sm,
  },
  quizCtaPillText: {
    color: '#FFFFFF',
    fontSize: typography.xs - 1,
    fontWeight: typography.black,
    letterSpacing: 1.2,
  },

  quizResultsCard: {
    borderRadius: radius.xl,
    padding: spacing.base,
    overflow: 'hidden',
    position: 'relative',
    ...shadows.lg,
  },
  quizMeta: {
    color: 'rgba(255,255,255,0.85)',
    fontSize: typography.xs,
    fontWeight: typography.medium,
    marginTop: spacing.sm,
  },
  intentoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    padding: 10,
    borderRadius: radius.md,
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.10)',
  },
  intentoNum: {
    width: 32, height: 32,
    borderRadius: radius.full,
    backgroundColor: 'rgba(255,255,255,0.15)',
    alignItems: 'center', justifyContent: 'center',
  },
  intentoNumText: {
    color: '#FFFFFF',
    fontSize: typography.xs,
    fontWeight: typography.black,
  },
  intentoMain: {
    color: '#FFFFFF',
    fontSize: typography.sm,
    fontWeight: typography.black,
  },
  intentoMeta: {
    color: 'rgba(255,255,255,0.65)',
    fontSize: typography.xs - 1,
    fontWeight: typography.medium,
    marginTop: 1,
  },
  intentoBar: {
    width: 60,
    height: 6,
    borderRadius: 3,
    backgroundColor: 'rgba(255,255,255,0.10)',
    overflow: 'hidden',
  },
  intentoBarFill: { height: '100%', borderRadius: 3 },
  quizRetryBtn: {
    marginTop: spacing.base,
    borderRadius: radius.full,
    overflow: 'hidden',
    alignSelf: 'flex-start',
    ...shadows.brand,
  },
  quizRetryGrad: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    paddingVertical: 11,
    paddingHorizontal: spacing.md,
  },
  quizRetryText: {
    color: '#FFFFFF',
    fontSize: typography.sm,
    fontWeight: typography.black,
  },
  quizDoneTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    alignSelf: 'flex-start',
    paddingHorizontal: spacing.sm,
    paddingVertical: 6,
    borderRadius: radius.full,
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.10)',
    marginTop: spacing.base,
  },
  quizDoneText: {
    color: 'rgba(255,255,255,0.85)',
    fontSize: typography.xs,
    fontWeight: typography.bold,
  },

  footerInfo: {
    fontSize: typography.xs,
    fontWeight: typography.medium,
  },
});
