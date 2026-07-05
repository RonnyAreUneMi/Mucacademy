import { useEffect, useState, useCallback } from 'react';
import {
  Linking, Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import RenderHTML from 'react-native-render-html';

import { api } from '@/api/client';
import {
  brandScale, colors, navyScale, radius, shadows, spacing, themed, typography,
} from '@/theme/tokens';
import { useTheme } from '@/stores/theme';
import {
  Badge, BettoLogo, BottomSheet, Button, Loader, MeetLogo, NeuCard, StepCard, useToast,
} from '@/components/ui';

type Status = 'asisti' | 'inscrito' | 'no_asisti' | 'disponible';
type EventDetail = {
  id: number;
  title: string;
  titulo_display: string;
  description: string;
  date: string;
  day_of_week: string;
  start_time: string;
  end_time: string;
  modality: string;
  es_virtual: boolean;
  meeting_url: string;
  location: string;
  banner_url: string | null;
  status: Status;
  has_resumen?: boolean;
  lote_nombre: string | null;
  horas: number | null;
  capacidad: number;
  cupos_ocupados: number;
  cupos_disponibles: number | null;
};

const STATUS_TONE: Record<Status, 'success' | 'brand' | 'danger' | 'info'> = {
  asisti: 'success', inscrito: 'brand', no_asisti: 'danger', disponible: 'info',
};
const STATUS_LABEL: Record<Status, string> = {
  asisti: 'Asistí', inscrito: 'Inscrito', no_asisti: 'No asistí', disponible: 'Disponible',
};

export default function EventDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [data, setData] = useState<EventDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const insets = useSafeAreaInsets();
  const theme = useTheme();
  const t = themed(theme);
  const toast = useToast();

  const load = useCallback(async () => {
    try {
      const res = await api.get<EventDetail>(`/api/v1/public/account/events/${id}/`);
      setData(res);
    } catch (e: any) {
      toast.error(e?.message ?? 'No pudimos cargar el evento.', 'Error');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  async function inscribir() {
    setSubmitting(true);
    try {
      await api.post(`/api/v1/public/account/events/${id}/register/`);
      setConfirmOpen(false);
      toast.success('Te inscribiste al evento.', '¡Listo!');
      await load();
    } catch (e: any) {
      toast.error(e?.message ?? 'No pudimos inscribirte.', 'Error');
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <SafeAreaView style={[styles.safe, { backgroundColor: t.bg }]}>
        <View style={styles.loading}><Loader size={88} /></View>
      </SafeAreaView>
    );
  }
  if (!data) return null;

  const formattedDate = formatDate(data.date);
  const horaInicio = data.start_time.slice(0, 5);
  const horaFin = data.end_time.slice(0, 5);
  const showInscribirCTA = data.status === 'disponible';
  const isInscrito = data.status === 'inscrito';

  return (
    <View style={[styles.safe, { backgroundColor: t.bg }]}>
      <ScrollView
        contentContainerStyle={{ paddingBottom: 120 + insets.bottom }}
        showsVerticalScrollIndicator={false}
      >
        {/* HERO */}
        <View style={styles.hero}>
          <LinearGradient
            colors={data.es_virtual
              ? ['#1E3A8A', '#1E40AF', '#0F1F4D'] as [string, string, string]
              : [brandScale[500], '#E8721C', brandScale[700]] as [string, string, string]
            }
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={StyleSheet.absoluteFillObject}
          />
          <LinearGradient
            colors={['transparent', 'rgba(0,0,0,0.55)'] as [string, string]}
            style={StyleSheet.absoluteFillObject}
          />
          <View style={styles.heroDecor}>
            <Ionicons
              name={data.es_virtual ? 'videocam' : 'business'}
              size={220}
              color="rgba(255,255,255,0.08)"
            />
          </View>

          {/* Back button sobre hero */}
          <Pressable
            onPress={() => router.back()}
            style={({ pressed }) => [
              styles.backBtn,
              { top: insets.top + spacing.sm },
              pressed && { opacity: 0.7 },
            ]}
            hitSlop={10}
          >
            <Ionicons name="chevron-back" size={22} color="#FFFFFF" />
          </Pressable>

          {/* Hero content */}
          <View style={styles.heroContent}>
            <View style={{ flexDirection: 'row', gap: spacing.xs }}>
              <Badge
                tone={data.es_virtual ? 'info' : 'brand'}
                variant="solid"
                size="md"
                iconLeft={
                  <Ionicons
                    name={data.es_virtual ? 'videocam' : 'business'}
                    size={12}
                    color="#FFFFFF"
                  />
                }
              >
                {data.es_virtual ? 'Virtual' : 'Presencial'}
              </Badge>
              <Badge tone={STATUS_TONE[data.status]} variant="soft" size="md" dot>
                {STATUS_LABEL[data.status]}
              </Badge>
            </View>

            <Text style={styles.heroTitle}>{data.titulo_display}</Text>

            <View style={styles.heroMeta}>
              <View style={styles.heroMetaItem}>
                <Ionicons name="calendar" size={14} color={brandScale[300]} />
                <Text style={styles.heroMetaText}>{formattedDate}</Text>
              </View>
              <View style={styles.heroMetaItem}>
                <Ionicons name="time" size={14} color={brandScale[300]} />
                <Text style={styles.heroMetaText}>{horaInicio}–{horaFin}</Text>
              </View>
            </View>
          </View>
        </View>

        {/* ═══ ACCIONES PRINCIPALES (contenedor neumorfista) ═══ */}
        {isInscrito || data.status === 'asisti' ? (
          <View style={[styles.section]}>
            <View style={[
              styles.actionsBlock,
              {
                backgroundColor: t.cardSoft,
                borderColor: t.border,
              },
              shadows.lg,
            ]}>
              <View style={styles.actionsHead}>
                <View style={[styles.actionsHeadIcon, { backgroundColor: 'rgba(245,136,48,0.14)' }]}>
                  <Ionicons name="flash" size={14} color={colors.brand} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={[styles.actionsEyebrow, { color: colors.brand }]}>ACCIONES</Text>
                  <Text style={[styles.actionsTitle, { color: t.text }]}>
                    {data.status === 'asisti' ? 'Asistencia registrada ✓' : '¿Qué querés hacer?'}
                  </Text>
                </View>
              </View>

              {/* Resumen de Betto — solo si YA existe un resumen listo y el usuario es parte del evento */}
              {data.has_resumen && (data.status === 'asisti' || data.status === 'inscrito' || data.status === 'no_asisti') ? (
                <BettoSummaryButton sesionId={data.id} />
              ) : null}

              {/* Acciones del día del evento (Meet / QR) si aún no se cerró */}
              {data.status !== 'asisti' ? (
                <>
                  {/* MEET — para virtuales que aún no asistieron */}
                  {data.es_virtual && data.meeting_url ? (
                    <Button
                      tone="info"
                      variant="filled"
                      size="lg"
                      fullWidth
                      iconLeft={<MeetLogo size={20} />}
                      iconRight={<Ionicons name="open-outline" size={16} color="#FFFFFF" />}
                      onPress={() => Linking.openURL(data.meeting_url)}
                    >
                      Abrir reunión Meet
                    </Button>
                  ) : null}

                  {/* ESCANEAR QR — para presenciales aún sin asistir */}
                  {!data.es_virtual ? (
                    <Button
                      tone="brand"
                      variant="filled"
                      size="lg"
                      fullWidth
                      iconLeft={<Ionicons name="qr-code" size={20} color="#FFFFFF" />}
                      onPress={() => router.push('/scanner')}
                    >
                      Escanear QR de asistencia
                    </Button>
                  ) : null}
                </>
              ) : null}
            </View>
          </View>
        ) : null}

        {/* INFO RÁPIDA */}
        <View style={styles.infoGrid}>
          <InfoTile
            icon={data.es_virtual ? 'globe-outline' : 'location-outline'}
            label={data.es_virtual ? 'Plataforma' : 'Lugar'}
            value={data.es_virtual ? 'En línea' : (data.location || 'Por confirmar')}
            tint={data.es_virtual ? '#3B82F6' : colors.brand}
          />
          <InfoTile
            icon="people-outline"
            label="Cupos"
            value={
              data.capacidad === 0
                ? 'Ilimitados'
                : `${data.cupos_disponibles ?? 0} / ${data.capacidad}`
            }
            tint="#A855F7"
          />
          {data.horas ? (
            <InfoTile
              icon="hourglass-outline"
              label="Horas válidas"
              value={`${data.horas}h`}
              tint="#10B981"
            />
          ) : null}
          {data.lote_nombre ? (
            <InfoTile
              icon="ribbon-outline"
              label="Programa"
              value={data.lote_nombre}
              tint="#F59E0B"
            />
          ) : null}
        </View>

        {/* BENEFICIOS */}
        <View style={styles.section}>
          <Text style={[styles.sectionEyebrow, { color: colors.brand }]}>QUÉ VAS A OBTENER</Text>
          <Text style={[styles.sectionTitle, { color: t.text }]}>Beneficios</Text>
          <View style={{ gap: spacing.sm, marginTop: spacing.base }}>
            <StepCard
              icon="checkmark-circle"
              title="Asiste al evento"
              text="Confirma tu asistencia con un solo click. Recibirás recordatorios."
              color="brand"
            />
            <StepCard
              icon="ribbon"
              title="Certificado digital"
              text="Al finalizar recibís tu certificado en PDF, verificable con QR."
              color="success"
            />
            <StepCard
              icon="time"
              title="Horas validadas"
              text={data.horas
                ? `Suma ${data.horas} horas a tu portafolio académico.`
                : 'Suma horas válidas a tu portafolio académico.'}
              color="info"
            />
            <StepCard
              icon="sparkles"
              title="Resúmenes con IA"
              text="Acceso al resumen del evento generado con inteligencia artificial."
              color="violet"
            />
          </View>
        </View>

        {/* DESCRIPCIÓN — render HTML real (negritas, listas, h2, etc.) */}
        {data.description ? (
          <View style={styles.section}>
            <Text style={[styles.sectionEyebrow, { color: colors.brand }]}>ACERCA DEL EVENTO</Text>
            <Text style={[styles.sectionTitle, { color: t.text }]}>Detalles</Text>
            <NeuCard style={{ marginTop: spacing.base }}>
              <RichDescription html={data.description} />
            </NeuCard>
          </View>
        ) : null}

      </ScrollView>

      {/* CTA STICKY ABAJO */}
      {showInscribirCTA ? (
        <View style={[styles.sticky, { paddingBottom: insets.bottom + spacing.base }]}>
          <View style={[styles.stickyInner, { backgroundColor: t.cardSoft, borderColor: t.border }]}>
            <View style={{ flex: 1 }}>
              <Text style={[styles.stickyHint, { color: t.textMuted }]}>
                {data.cupos_disponibles && data.capacidad > 0
                  ? `${data.cupos_disponibles} cupos disponibles`
                  : 'Inscripción abierta'}
              </Text>
              <Text style={[styles.stickyTitle, { color: t.text }]}>Te interesa este evento?</Text>
            </View>
            <Button
              tone="brand"
              variant="filled"
              size="lg"
              onPress={() => setConfirmOpen(true)}
              iconRight={<Ionicons name="arrow-forward" size={16} color="#FFFFFF" />}
            >
              Inscribirme
            </Button>
          </View>
        </View>
      ) : null}

      {/* SHEET DE CONFIRMACIÓN */}
      <BottomSheet
        visible={confirmOpen}
        onClose={() => !submitting && setConfirmOpen(false)}
        title="Confirmar inscripción"
      >
        <Text style={[styles.confirmText, { color: t.textMuted }]}>
          Te vas a inscribir a:
        </Text>
        <NeuCard style={{ marginTop: spacing.base }}>
          <Text style={[styles.confirmEvent, { color: t.text }]} numberOfLines={2}>
            {data.titulo_display}
          </Text>
          <View style={styles.confirmMetaRow}>
            <View style={styles.confirmMetaItem}>
              <Ionicons name="calendar-outline" size={14} color={t.textMuted} />
              <Text style={[styles.confirmMetaText, { color: t.textMuted }]}>
                {formattedDate} · {horaInicio}
              </Text>
            </View>
          </View>
        </NeuCard>

        <View style={styles.confirmFooter}>
          <Button
            tone="neutral"
            variant="ghost"
            size="lg"
            onPress={() => setConfirmOpen(false)}
            disabled={submitting}
          >
            Cancelar
          </Button>
          <Button
            tone="brand"
            variant="filled"
            size="lg"
            loading={submitting}
            onPress={inscribir}
            iconRight={!submitting ? <Ionicons name="checkmark" size={18} color="#FFFFFF" /> : undefined}
          >
            Confirmar
          </Button>
        </View>
      </BottomSheet>
    </View>
  );
}

// ── Subcomponentes ────────────────────────────────────────────────

/**
 * BettoSummaryButton — botón destacado para acceder al resumen IA del evento.
 * Solo se muestra cuando el participante YA registró asistencia. Por ahora
 * el resumen está en construcción → toast "aún estamos cargando".
 */
function BettoSummaryButton({ sesionId }: { sesionId: number }) {
  const t = themed(useTheme());

  function handlePress() {
    router.push(`/event/resumen/${sesionId}`);
  }

  return (
    <Pressable
      onPress={handlePress}
      style={({ pressed }) => [
        styles.bettoBtn,
        { backgroundColor: t.cardSoft, borderColor: t.border },
        pressed && { opacity: 0.85, transform: [{ scale: 0.98 }] },
      ]}
    >
      <BettoLogo size={42} />
      <View style={{ flex: 1 }}>
        <Text style={[styles.bettoTitle, { color: t.text }]}>Ver resumen de Betto</Text>
        <Text style={[styles.bettoSub, { color: t.textMuted }]}>
          IA · Puntos clave + cuestionario del evento
        </Text>
      </View>
      <View style={styles.bettoBadge}>
        <Ionicons name="sparkles" size={11} color={colors.brand} />
        <Text style={styles.bettoBadgeText}>BETTO</Text>
      </View>
    </Pressable>
  );
}

function InfoTile({
  icon, label, value, tint = colors.brand,
}: {
  icon: React.ComponentProps<typeof Ionicons>['name'];
  label: string;
  value: string;
  tint?: string;
}) {
  const t = themed(useTheme());
  return (
    <View style={[styles.infoTile, { backgroundColor: t.cardSoft, borderColor: t.border }]}>
      <View style={[styles.infoIconWrap, { backgroundColor: hexAlpha(tint, 0.14) }]}>
        <Ionicons name={icon} size={16} color={tint} />
      </View>
      <Text style={[styles.infoLabel, { color: t.textMuted }]} numberOfLines={1}>{label}</Text>
      <Text style={[styles.infoValue, { color: t.text }]} numberOfLines={1}>{value}</Text>
    </View>
  );
}

/** Mezcla un color hex con alpha (devuelve rgba). */
function hexAlpha(hex: string, alpha: number): string {
  const m = hex.replace('#', '');
  const r = parseInt(m.slice(0, 2), 16);
  const g = parseInt(m.slice(2, 4), 16);
  const b = parseInt(m.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// ── Helpers ───────────────────────────────────────────────────────

/** Renderiza HTML del CKEditor (negritas, listas, h2, p, strong) con
 *  estilos coherentes con el tema. Usa react-native-render-html. */
function RichDescription({ html }: { html: string }) {
  const { width } = useWindowDimensions();
  const t = themed(useTheme());

  return (
    <RenderHTML
      contentWidth={width - spacing.xl * 2 - spacing.base * 2}
      source={{ html }}
      systemFonts={['System']}
      baseStyle={{
        color: t.textMuted,
        fontSize: typography.sm,
        lineHeight: typography.sm * 1.55,
        fontWeight: typography.regular,
      }}
      tagsStyles={{
        p:      { marginVertical: 6 },
        strong: { color: t.text, fontWeight: typography.black },
        b:      { color: t.text, fontWeight: typography.black },
        em:     { fontStyle: 'italic' },
        h2:     { color: t.text, fontSize: typography.md, fontWeight: typography.black, marginTop: spacing.base, marginBottom: spacing.xs, letterSpacing: -0.2 },
        h3:     { color: t.text, fontSize: typography.base, fontWeight: typography.black, marginTop: spacing.sm, marginBottom: 2 },
        ul:     { marginVertical: 4, paddingLeft: 6 },
        ol:     { marginVertical: 4, paddingLeft: 6 },
        li:     { marginVertical: 2 },
        a:      { color: colors.brand, fontWeight: typography.bold, textDecorationLine: 'underline' },
      }}
      defaultTextProps={{ selectable: true }}
      enableExperimentalMarginCollapsing
    />
  );
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso + 'T00:00:00');
    return d.toLocaleDateString('es-EC', { day: '2-digit', month: 'long', year: 'numeric' });
  } catch {
    return iso;
  }
}

// ── Estilos ───────────────────────────────────────────────────────
const HERO_HEIGHT = 320;

const styles = StyleSheet.create({
  safe: { flex: 1 },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },

  hero: {
    height: HERO_HEIGHT,
    justifyContent: 'flex-end',
    overflow: 'hidden',
  },
  heroDecor: {
    position: 'absolute',
    right: -30, bottom: -30,
  },
  backBtn: {
    position: 'absolute',
    left: spacing.base,
    width: 38, height: 38,
    borderRadius: radius.full,
    backgroundColor: 'rgba(0,0,0,0.35)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.18)',
    alignItems: 'center', justifyContent: 'center',
    zIndex: 5,
  },
  heroContent: {
    padding: spacing.xl,
    gap: spacing.sm,
  },
  heroTitle: {
    color: '#FFFFFF',
    fontSize: typography.xxl,
    fontWeight: typography.black,
    letterSpacing: -0.5,
    lineHeight: typography.xxl * 1.1,
  },
  heroMeta: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    marginTop: spacing.xs,
  },
  heroMetaItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  heroMetaText: {
    color: 'rgba(255,255,255,0.92)',
    fontSize: typography.sm,
    fontWeight: typography.medium,
  },

  infoGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.lg,
  },
  infoTile: {
    flexBasis: '48%',
    flexGrow: 1,
    padding: spacing.base,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.xs,
  },
  infoIconWrap: {
    width: 30, height: 30,
    borderRadius: radius.md,
    alignItems: 'center', justifyContent: 'center',
    marginBottom: spacing.xs,
  },
  infoLabel: {
    fontSize: typography.xs,
    fontWeight: typography.bold,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
  },
  infoValue: {
    fontSize: typography.base,
    fontWeight: typography.bold,
  },

  section: {
    paddingHorizontal: spacing.xl,
    marginTop: spacing.xl,
  },
  actionsBlock: {
    gap: spacing.md,
    marginTop: spacing.lg,
    padding: spacing.base,
    borderRadius: radius.xl,
    borderWidth: 1,
  },
  actionsHead: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.xs,
  },
  actionsHeadIcon: {
    width: 28, height: 28,
    borderRadius: radius.md,
    alignItems: 'center', justifyContent: 'center',
  },
  actionsEyebrow: {
    fontSize: typography.xs - 1,
    fontWeight: typography.black,
    letterSpacing: 1.5,
  },
  actionsTitle: {
    fontSize: typography.base,
    fontWeight: typography.black,
    letterSpacing: -0.2,
    marginTop: 1,
  },

  // BettoSummaryButton (post-asistencia)
  bettoBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    padding: spacing.base,
    borderRadius: radius.lg,
    borderWidth: 1,
    ...shadows.md,
  },
  bettoTitle: {
    fontSize: typography.base,
    fontWeight: typography.black,
    letterSpacing: -0.2,
  },
  bettoSub: {
    fontSize: typography.xs,
    fontWeight: typography.medium,
    marginTop: 2,
  },
  bettoBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radius.full,
    backgroundColor: 'rgba(245,136,48,0.12)',
    borderWidth: 1,
    borderColor: 'rgba(245,136,48,0.30)',
  },
  bettoBadgeText: {
    color: colors.brand,
    fontSize: typography.xs - 2,
    fontWeight: typography.black,
    letterSpacing: 1.5,
  },
  sectionEyebrow: {
    fontSize: typography.xs,
    fontWeight: typography.black,
    letterSpacing: 1.4,
    marginBottom: spacing.xs,
  },
  sectionTitle: {
    fontSize: typography.xl,
    fontWeight: typography.black,
    letterSpacing: -0.3,
  },
  descripcion: {
    fontSize: typography.sm,
    lineHeight: typography.sm * 1.55,
  },

  sticky: {
    position: 'absolute',
    bottom: 0, left: 0, right: 0,
    paddingHorizontal: spacing.base,
    paddingTop: spacing.sm,
  },
  stickyInner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    padding: spacing.base,
    borderRadius: radius.xl,
    borderWidth: 1,
    ...shadows.lg,
  },
  stickyHint: {
    fontSize: typography.xs,
    fontWeight: typography.bold,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
  },
  stickyTitle: {
    fontSize: typography.base,
    fontWeight: typography.black,
    marginTop: 2,
  },

  confirmText: {
    fontSize: typography.sm,
    fontWeight: typography.medium,
  },
  confirmEvent: {
    fontSize: typography.lg,
    fontWeight: typography.black,
    letterSpacing: -0.2,
  },
  confirmMetaRow: {
    flexDirection: 'row',
    gap: spacing.md,
    marginTop: spacing.sm,
  },
  confirmMetaItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  confirmMetaText: {
    fontSize: typography.sm,
    fontWeight: typography.medium,
  },
  confirmFooter: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.xl,
    justifyContent: 'flex-end',
  },
});
