import { useEffect, useRef, useState, useCallback } from 'react';
import {
  Dimensions, Linking, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, {
  Easing, FadeInDown, useAnimatedStyle, useSharedValue, withDelay, withTiming,
} from 'react-native-reanimated';

import { api } from '@/api/client';
import {
  brandScale, colors, radius, shadows, spacing, TAB_BAR_HEIGHT,
  themed, typography,
} from '@/theme/tokens';
import { useAuth } from '@/stores/auth';
import { useTheme } from '@/stores/theme';
import {
  Badge, GlassCard, GradientText, Loader, MeetLogo, VBackground,
} from '@/components/ui';

const { width: SCREEN_W } = Dimensions.get('window');
const CERT_CARD_W = Math.min(220, SCREEN_W * 0.62);
const CERT_CARD_H = 240;
const RECO_CARD_W = Math.min(200, SCREEN_W * 0.55);

type Stats = {
  certificados: number;
  total_horas: number;
  eventos_inscrito: number;
  eventos_asistido: number;
};
type Event = {
  id: number;
  titulo_display: string;
  date: string;
  start_time: string;
  end_time: string;
  es_virtual: boolean;
  meeting_url?: string;
  location?: string;
};
type Certificate = {
  id: number;
  course: string;
  course_date: string | null;
  hours: number;
  download_url: string;
};
type DashboardData = {
  stats: Stats;
  proximos: Event[];
  recomendados: Event[];
  certificados_recientes?: Certificate[];
};

export default function DashboardScreen() {
  const participante = useAuth((s) => s.participante);
  const [data, setData]       = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const theme = useTheme();
  const t = themed(theme);

  const load = useCallback(async () => {
    try {
      const res = await api.get<DashboardData>('/api/v1/public/account/dashboard/');
      setData(res);
    } catch {
      // silencio
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <SafeAreaView style={[styles.safe, { backgroundColor: t.bg }]}>
        <View style={styles.loading}><Loader size={88} label="Cargando tu cuenta…" /></View>
      </SafeAreaView>
    );
  }

  const today = new Date();
  const greeting = getGreeting(today);
  const dateBlock = formatDateBlock(today);
  const nextEvent = data?.proximos?.[0];

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: t.bg }]}>
      <VBackground intensity={theme === 'dark' ? 0.7 : 0.4} />
      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => { setRefreshing(true); load(); }}
            tintColor={colors.brand}
          />
        }
      >
        {/* ═══ HERO SALUDO — solo lo esencial: saludo · nombre · fecha ═══ */}
        <View style={styles.hero}>
          <View style={styles.heroRow}>
            <View style={{ flex: 1 }}>
              <Text style={[styles.heroEyebrow, { color: t.textMuted }]}>
                {greeting.label}
              </Text>
              <View style={styles.heroTitleWrap}>
                <GradientText style={styles.heroTitle}>
                  {`${(participante?.first_name || '—').split(' ')[0]}.`}
                </GradientText>
              </View>
            </View>

            {/* Fecha block (estilo iPhone calendar widget) */}
            <View style={[
              styles.dateBlock,
              {
                backgroundColor: theme === 'dark' ? 'rgba(245,136,48,0.10)' : '#FFFFFF',
                borderColor: theme === 'dark' ? 'rgba(245,136,48,0.30)' : 'rgba(245,136,48,0.40)',
              },
              shadows.sm,
            ]}>
              <Text style={[styles.dateWeekday, { color: colors.brand }]}>{dateBlock.weekday}</Text>
              <Text style={[styles.dateDay, { color: t.text }]}>{dateBlock.day}</Text>
              <Text style={[styles.dateMonth, { color: t.textMuted }]}>{dateBlock.month}</Text>
            </View>
          </View>
        </View>

        {/* ═══ STATS — tile certs (decorativo) + barra de progreso de horas ═══ */}
        <View style={styles.statsGrid}>
          <CertsStatCard count={data?.stats.certificados ?? 0} />
          <HoursProgressCard hours={data?.stats.total_horas ?? 0} goal={100} />
        </View>

        {/* ═══ PRÓXIMO EVENTO destacado con countdown ═══ */}
        {nextEvent ? (
          <View style={styles.section}>
            <NextEventCard evento={nextEvent} />
          </View>
        ) : null}

        {/* ═══ Próximos eventos (resto) ═══ */}
        {(data?.proximos.length ?? 0) > 1 ? (
          <Section title="MIS PRÓXIMOS EVENTOS" actionLabel="Ver todos" onAction={() => router.push('/(tabs)/events')}>
            {data!.proximos.slice(1).map((s) => <EventRow key={s.id} sesion={s} />)}
          </Section>
        ) : null}

        {/* ═══ Recomendados — auto-carrusel estilo Amazon ═══ */}
        {(data?.recomendados.length ?? 0) > 0 ? (
          <View style={styles.recosBlock}>
            <View style={[styles.sectionHead, { paddingHorizontal: spacing.xl }]}>
              <Text style={[styles.sectionTitle, { color: t.textMuted }]}>PARA TI · DISPONIBLES</Text>
              <Pressable onPress={() => router.push('/(tabs)/events')} hitSlop={6}>
                <Text style={styles.sectionAction}>Ver más →</Text>
              </Pressable>
            </View>
            <AutoCarousel
              data={data!.recomendados}
              itemWidth={RECO_CARD_W}
              gap={spacing.sm}
              keyExtractor={(s) => String(s.id)}
              renderItem={(s) => <RecoCard sesion={s} />}
              intervalMs={3500}
            />
          </View>
        ) : null}

        {/* ═══ Certificados recientes — auto-carrusel ═══ */}
        {(data?.certificados_recientes?.length ?? 0) > 0 ? (
          <View style={styles.certsBlock}>
            <View style={[styles.sectionHead, { paddingHorizontal: spacing.xl }]}>
              <Text style={[styles.sectionTitle, { color: t.textMuted }]}>ÚLTIMOS CERTIFICADOS</Text>
              <Pressable onPress={() => router.push('/(tabs)/certificates')} hitSlop={6}>
                <Text style={styles.sectionAction}>Ver todos →</Text>
              </Pressable>
            </View>
            <AutoCarousel
              data={data!.certificados_recientes!}
              itemWidth={CERT_CARD_W}
              gap={spacing.sm}
              keyExtractor={(c) => String(c.id)}
              renderItem={(c) => <CertCard cert={c} />}
              intervalMs={4500}
            />
          </View>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

// ── Subcomponentes ──────────────────────────────────────────────

/**
 * Carrusel horizontal con auto-scroll cíclico.
 * - Avanza al siguiente item cada `intervalMs` (default 3.5s)
 * - Cuando el usuario interactúa, pausa por `pauseAfterTouchMs` y reanuda
 * - Hace loop al volver al inicio cuando llega al final
 */
function AutoCarousel<T>({
  data, itemWidth, gap, renderItem, keyExtractor,
  intervalMs = 3500, pauseAfterTouchMs = 6000,
}: {
  data: T[];
  itemWidth: number;
  gap: number;
  renderItem: (item: T, index: number) => React.ReactNode;
  keyExtractor: (item: T) => string;
  intervalMs?: number;
  pauseAfterTouchMs?: number;
}) {
  const ref = useRef<ScrollView>(null);
  const idxRef = useRef(0);
  const pausedUntil = useRef(0);

  useEffect(() => {
    if (data.length <= 1) return;
    const tick = setInterval(() => {
      if (Date.now() < pausedUntil.current) return;
      idxRef.current = (idxRef.current + 1) % data.length;
      ref.current?.scrollTo({
        x: idxRef.current * (itemWidth + gap),
        animated: true,
      });
    }, intervalMs);
    return () => clearInterval(tick);
  }, [data.length, itemWidth, gap, intervalMs]);

  return (
    <ScrollView
      ref={ref}
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={{
        paddingHorizontal: spacing.xl,
        gap,
        paddingTop: spacing.sm,
      }}
      snapToInterval={itemWidth + gap}
      decelerationRate="fast"
      onScrollBeginDrag={() => { pausedUntil.current = Date.now() + pauseAfterTouchMs; }}
      onMomentumScrollEnd={(e) => {
        const x = e.nativeEvent.contentOffset.x;
        idxRef.current = Math.round(x / (itemWidth + gap));
        pausedUntil.current = Date.now() + pauseAfterTouchMs;
      }}
    >
      {data.map((item, i) => (
        <Animated.View
          key={keyExtractor(item)}
          entering={FadeInDown.delay(i * 80).springify().damping(14)}
        >
          {renderItem(item, i)}
        </Animated.View>
      ))}
    </ScrollView>
  );
}

function CertsStatCard({ count }: { count: number }) {
  const t = themed(useTheme());
  const scale = useSharedValue(0.7);

  useEffect(() => {
    scale.value = withDelay(
      200,
      withTiming(1, { duration: 700, easing: Easing.out(Easing.back(1.4)) }),
    );
  }, [scale]);

  const numStyle = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));

  return (
    <View style={[
      styles.certsCard,
      { backgroundColor: t.cardSoft, borderColor: t.border },
      shadows.sm,
    ]}>
      {/* Decoración: ribbon grande al fondo */}
      <Ionicons
        name="ribbon"
        size={120}
        color={brandScale[500]}
        style={styles.certsDecor}
      />
      {/* Mini icono brand pill arriba */}
      <View style={styles.certsBadge}>
        <Ionicons name="ribbon" size={11} color="#FFFFFF" />
      </View>

      <View style={styles.certsBody}>
        <Animated.Text style={[styles.certsNum, { color: t.text }, numStyle]}>
          {count}
        </Animated.Text>
        <Text style={[styles.certsLabel, { color: t.textMuted }]}>
          Certificado{count === 1 ? '' : 's'}
        </Text>
      </View>
    </View>
  );
}

function HoursProgressCard({ hours, goal }: { hours: number; goal: number }) {
  const t = themed(useTheme());
  const pct = Math.min(100, Math.round((hours / goal) * 100));
  const fillW = useSharedValue(0);

  useEffect(() => {
    // Animación al cargar: la barra crece desde 0 hasta el % real
    fillW.value = withDelay(
      300,
      withTiming(pct, { duration: 1100, easing: Easing.out(Easing.cubic) }),
    );
  }, [pct, fillW]);

  const fillStyle = useAnimatedStyle(() => ({
    width: `${fillW.value}%` as `${number}%`,
  }));

  return (
    <View style={[
      styles.hoursCard,
      { backgroundColor: t.cardSoft, borderColor: t.border },
      shadows.sm,
    ]}>
      {/* Decoración: reloj grande al fondo (mismo patrón que la card de certs) */}
      <Ionicons
        name="time"
        size={120}
        color="#A855F7"
        style={styles.hoursDecor}
      />
      {/* Mini badge brand violeta arriba */}
      <View style={styles.hoursBadge}>
        <Ionicons name="time" size={11} color="#FFFFFF" />
      </View>

      <View style={styles.hoursBody}>
        <Text style={[styles.hoursValue, { color: t.text }]}>
          {hours}<Text style={[styles.hoursSuffix, { color: t.textMuted }]}>h</Text>
        </Text>
        <Text style={[styles.hoursLabel, { color: t.textMuted }]}>de {goal}h</Text>
      </View>

      {/* Barra de progreso animada */}
      <View style={styles.hoursBarTrack}>
        <Animated.View style={[styles.hoursBarFillWrap, fillStyle]}>
          <LinearGradient
            colors={['#A855F7', '#7C3AED', '#6D28D9']}
            start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
            style={styles.hoursBarFill}
          />
        </Animated.View>
      </View>

      <View style={styles.hoursMetaRow}>
        <Text style={[styles.hoursMetaText, { color: t.textMuted }]}>
          {pct}% completado
        </Text>
        <Text style={[styles.hoursMetaText, { color: '#A855F7', fontWeight: typography.black }]}>
          Meta {goal}h
        </Text>
      </View>
    </View>
  );
}

function StatTile({
  icon, value, suffix, label, gradient,
}: {
  icon: React.ComponentProps<typeof Ionicons>['name'];
  value: string | number;
  suffix?: string;
  label: string;
  gradient: [string, string];
}) {
  const t = themed(useTheme());
  return (
    <View style={[
      styles.stat,
      { backgroundColor: t.cardSoft, borderColor: t.border },
      shadows.sm,
    ]}>
      <LinearGradient
        colors={gradient}
        start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
        style={styles.statIcon}
      >
        <Ionicons name={icon} size={16} color="#FFFFFF" />
      </LinearGradient>
      <View style={{ flex: 1 }}>
        <Text style={[styles.statValue, { color: t.text }]}>
          {value}
          {suffix ? <Text style={[styles.statSuffix, { color: t.textMuted }]}>{suffix}</Text> : null}
        </Text>
        <Text style={[styles.statLabel, { color: t.textMuted }]}>{label}</Text>
      </View>
    </View>
  );
}

function NextEventCard({ evento }: { evento: Event }) {
  const theme = useTheme();
  const t = themed(theme);
  const targetDate = new Date(`${evento.date}T${evento.start_time}`);
  const [remaining, setRemaining] = useState(() => calcRemaining(targetDate));

  useEffect(() => {
    // Refresh cada 60s — la pill solo muestra la unidad mayor (días/horas/min)
    // así que no hace falta un timer por segundo.
    const timer = setInterval(() => setRemaining(calcRemaining(targetDate)), 60000);
    return () => clearInterval(timer);
  }, [evento.date, evento.start_time]);

  return (
    <GlassCard onPress={() => router.push({ pathname: '/event/[id]', params: { id: String(evento.id) } })}>
      <View style={styles.nextHead}>
        <Badge tone="brand" variant="soft" size="sm" iconLeft={<Ionicons name="flash" size={11} color={colors.brand} />}>
          PRÓXIMO EVENTO
        </Badge>
        <Badge
          tone={evento.es_virtual ? 'info' : 'brand'}
          variant="solid"
          size="sm"
          iconLeft={
            <Ionicons name={evento.es_virtual ? 'videocam' : 'business'} size={11} color="#FFFFFF" />
          }
        >
          {evento.es_virtual ? 'Virtual' : 'Presencial'}
        </Badge>
      </View>

      <Text style={[styles.nextTitle, { color: t.text }]} numberOfLines={2}>
        {evento.titulo_display}
      </Text>

      <View style={styles.nextMeta}>
        <View style={styles.nextMetaItem}>
          <Ionicons name="calendar" size={13} color={colors.brand} />
          <Text style={[styles.nextMetaText, { color: t.textMuted }]}>
            {formatDate(evento.date)}
          </Text>
        </View>
        <View style={styles.nextMetaItem}>
          <Ionicons name="time" size={13} color={colors.brand} />
          <Text style={[styles.nextMetaText, { color: t.textMuted }]}>
            {evento.start_time.slice(0, 5)}
          </Text>
        </View>
      </View>

      {/* Countdown compacto — solo la unidad más relevante */}
      <View style={styles.countdownPill}>
        <Ionicons name="hourglass" size={14} color={colors.brand} />
        <Text style={[styles.countdownText, { color: t.text }]}>
          {countdownLabel(remaining)}
        </Text>
      </View>

      {/* Botón Meet — sin caja propia, solo contenido dentro del GlassCard */}
      {evento.es_virtual && evento.meeting_url ? (
        <Pressable
          onPress={(e: any) => {
            e?.stopPropagation?.();
            Linking.openURL(evento.meeting_url!);
          }}
          style={({ pressed }) => [
            styles.meetBtn,
            pressed && { opacity: 0.7 },
          ]}
        >
          <MeetLogo size={32} />
          <View style={{ flex: 1 }}>
            <Text style={[styles.meetText, { color: t.text }]}>Entrar a Google Meet</Text>
            <Text style={[styles.meetSub, { color: t.textMuted }]}>Reunión virtual</Text>
          </View>
          <View style={styles.meetGo}>
            <Ionicons name="arrow-forward" size={16} color="#FFFFFF" />
          </View>
        </Pressable>
      ) : null}
    </GlassCard>
  );
}

function Section({
  title, children, actionLabel, onAction,
}: {
  title: string;
  children: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
}) {
  const t = themed(useTheme());
  return (
    <View style={styles.section}>
      <View style={styles.sectionHead}>
        <Text style={[styles.sectionTitle, { color: t.textMuted }]}>{title}</Text>
        {actionLabel && onAction ? (
          <Pressable onPress={onAction} hitSlop={6}>
            <Text style={styles.sectionAction}>{actionLabel} →</Text>
          </Pressable>
        ) : null}
      </View>
      <View style={{ gap: spacing.sm }}>{children}</View>
    </View>
  );
}

function EventRow({ sesion }: { sesion: Event }) {
  const t = themed(useTheme());
  return (
    <GlassCard onPress={() => router.push({ pathname: '/event/[id]', params: { id: String(sesion.id) } })}>
      <View style={styles.rowTop}>
        <Badge
          tone={sesion.es_virtual ? 'info' : 'brand'}
          variant="solid"
          size="sm"
          iconLeft={<Ionicons name={sesion.es_virtual ? 'videocam' : 'business'} size={11} color="#FFFFFF" />}
        >
          {sesion.es_virtual ? 'Virtual' : 'Presencial'}
        </Badge>
      </View>
      <Text style={[styles.rowTitle, { color: t.text }]} numberOfLines={2}>
        {sesion.titulo_display}
      </Text>
      <View style={styles.rowMeta}>
        <Ionicons name="calendar-outline" size={13} color={t.textMuted} />
        <Text style={[styles.rowMetaText, { color: t.textMuted }]}>
          {formatDate(sesion.date)} · {sesion.start_time.slice(0, 5)}
        </Text>
      </View>
    </GlassCard>
  );
}

function RecoCard({ sesion }: { sesion: Event }) {
  const t = themed(useTheme());
  const heroColors: [string, string, string] = sesion.es_virtual
    ? ['#1E3A8A', '#1E40AF', '#0F1F4D']
    : [brandScale[500], '#E8721C', brandScale[700]];
  const dateBlock = dayBlockFromIso(sesion.date);

  return (
    <Pressable
      onPress={() => router.push({ pathname: '/event/[id]', params: { id: String(sesion.id) } })}
      style={({ pressed }) => [
        styles.recoCard,
        { backgroundColor: t.cardSoft, borderColor: t.border },
        pressed && { transform: [{ scale: 0.97 }], opacity: 0.92 },
      ]}
    >
      {/* Hero con gradient/banner */}
      <View style={styles.recoHero}>
        <LinearGradient
          colors={heroColors}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={StyleSheet.absoluteFill}
        />
        <Ionicons
          name={sesion.es_virtual ? 'videocam' : 'business'}
          size={70}
          color="rgba(255,255,255,0.15)"
          style={styles.recoDecor}
        />

        {/* Pill modalidad */}
        <View style={styles.recoModPill}>
          <Ionicons
            name={sesion.es_virtual ? 'videocam' : 'business'}
            size={9}
            color="#FFFFFF"
          />
          <Text style={styles.recoModText}>
            {sesion.es_virtual ? 'Virtual' : 'Presencial'}
          </Text>
        </View>

        {/* Day block */}
        <View style={styles.recoDateBlock}>
          <Text style={styles.recoDateDay}>{dateBlock.day}</Text>
          <Text style={styles.recoDateMonth}>{dateBlock.month}</Text>
        </View>
      </View>

      {/* Body */}
      <View style={styles.recoBody}>
        <Text style={[styles.recoTitle, { color: t.text }]} numberOfLines={2}>
          {sesion.titulo_display}
        </Text>
        <View style={styles.recoMetaRow}>
          <Ionicons name="time" size={11} color={colors.brand} />
          <Text style={[styles.recoMeta, { color: t.textMuted }]} numberOfLines={1}>
            {sesion.start_time.slice(0, 5)} h
          </Text>
        </View>
      </View>
    </Pressable>
  );
}

function CertCard({ cert }: { cert: Certificate }) {
  const t = themed(useTheme());
  return (
    <Pressable
      onPress={() => Linking.openURL(`${api.baseUrl}${cert.download_url}`)}
      style={({ pressed }) => [
        styles.certCard,
        pressed && { transform: [{ scale: 0.97 }], opacity: 0.92 },
      ]}
    >
      <LinearGradient
        colors={[brandScale[500], '#E8721C', brandScale[700]]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.certCardInner}
      >
        {/* Decoración: ribbon gigante semi-transparente */}
        <Ionicons
          name="ribbon"
          size={140}
          color="rgba(255,255,255,0.10)"
          style={styles.certDecor}
        />

        {/* Top: pill horas + ícono download */}
        <View style={styles.certTopRow}>
          <View style={styles.certHoursPill}>
            <Ionicons name="time" size={11} color="#FFFFFF" />
            <Text style={styles.certHoursText}>{cert.hours}h</Text>
          </View>
          <View style={styles.certDownloadCircle}>
            <Ionicons name="download" size={13} color="#FFFFFF" />
          </View>
        </View>

        {/* Middle: icono ribbon medallion grande */}
        <View style={styles.certMedalWrap}>
          <View style={styles.certMedal}>
            <Ionicons name="ribbon" size={36} color={colors.brand} />
          </View>
        </View>

        {/* Bottom: título + fecha */}
        <View style={{ marginTop: 'auto' }}>
          <Text style={styles.certEyebrow}>CERTIFICADO</Text>
          <Text style={styles.certTitleBig} numberOfLines={2}>{cert.course}</Text>
          {cert.course_date ? (
            <Text style={styles.certDate}>
              <Ionicons name="calendar" size={11} color="rgba(255,255,255,0.85)" />{' '}
              {formatDate(cert.course_date)}
            </Text>
          ) : null}
        </View>
      </LinearGradient>
    </Pressable>
  );
}

// ── Helpers ─────────────────────────────────────────────────────
function calcRemaining(target: Date) {
  const ms = target.getTime() - Date.now();
  if (ms <= 0) return { d: 0, h: 0, m: 0, s: 0, expired: true };
  const s = Math.floor(ms / 1000);
  return {
    d: Math.floor(s / 86400),
    h: Math.floor((s % 86400) / 3600),
    m: Math.floor((s % 3600) / 60),
    s: s % 60,
    expired: false,
  };
}

/** "2026-05-03" → { day: '03', month: 'MAY' } — para day blocks de cards. */
function dayBlockFromIso(iso: string): { day: string; month: string } {
  try {
    const d = new Date(`${iso}T00:00:00`);
    const months = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC'];
    return {
      day: String(d.getDate()).padStart(2, '0'),
      month: months[d.getMonth()],
    };
  } catch {
    return { day: '--', month: '---' };
  }
}

/** Texto humano de cuánto falta — solo la unidad mayor relevante. */
function countdownLabel(r: { d: number; h: number; m: number; expired: boolean }): string {
  if (r.expired) return 'Empezó · entrá ya';
  if (r.d > 0) return `Faltan ${r.d} día${r.d === 1 ? '' : 's'}`;
  if (r.h > 0) return `Faltan ${r.h} hora${r.h === 1 ? '' : 's'}`;
  if (r.m > 0) return `Faltan ${r.m} minuto${r.m === 1 ? '' : 's'}`;
  return 'Empieza en menos de 1 min';
}

function formatDate(iso: string): string {
  try {
    const d = new Date(`${iso}T00:00:00`);
    return d.toLocaleDateString('es-EC', { day: '2-digit', month: 'short' });
  } catch {
    return iso;
  }
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Saludo según hora local — buenas días/tardes/noches con icono apropiado. */
function getGreeting(now: Date): {
  label: string;
  icon: 'sunny' | 'partly-sunny' | 'moon';
} {
  const h = now.getHours();
  if (h >= 5 && h < 12)  return { label: 'Buenos días',   icon: 'sunny' };
  if (h >= 12 && h < 19) return { label: 'Buenas tardes', icon: 'partly-sunny' };
  return { label: 'Buenas noches', icon: 'moon' };
}

/** "Jueves, 30 de abril" → { weekday: 'JUE', day: '30', month: 'ABR' } */
function formatDateBlock(d: Date): { weekday: string; day: string; month: string } {
  const days   = ['DOM', 'LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB'];
  const months = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC'];
  return {
    weekday: days[d.getDay()],
    day: String(d.getDate()).padStart(2, '0'),
    month: months[d.getMonth()],
  };
}

// ── Estilos ─────────────────────────────────────────────────────
const styles = StyleSheet.create({
  safe:   { flex: 1 },
  scroll: { paddingBottom: TAB_BAR_HEIGHT + spacing.lg },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },

  hero: { paddingHorizontal: spacing.xl, paddingTop: spacing.sm, marginBottom: spacing.lg },
  heroRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.base,
  },
  heroEyebrow: {
    fontSize: typography.sm,
    fontWeight: typography.medium,
    letterSpacing: 0,
  },
  heroTitleWrap: { marginTop: 2 },
  heroTitle: {
    fontSize: typography.huge,
    fontWeight: typography.black,
    letterSpacing: -1,
    lineHeight: typography.huge * 1.05,
  },

  // Fecha block widget tipo iPhone Calendar
  dateBlock: {
    minWidth: 64,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.sm,
    borderRadius: radius.lg,
    borderWidth: 1,
    alignItems: 'center', justifyContent: 'center',
  },
  dateWeekday: {
    fontSize: typography.xs - 1,
    fontWeight: typography.black,
    letterSpacing: 1.5,
    textTransform: 'uppercase',
    lineHeight: typography.xs + 2,
  },
  dateDay: {
    fontSize: typography.xxl,
    fontWeight: typography.black,
    letterSpacing: -1,
    lineHeight: typography.xxl,
    marginVertical: 1,
  },
  dateMonth: {
    fontSize: typography.xs - 1,
    fontWeight: typography.bold,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
  },

  statsGrid: {
    flexDirection: 'row', flexWrap: 'wrap',
    paddingHorizontal: spacing.xl, gap: spacing.sm,
  },
  stat: {
    flexBasis: '48%', flexGrow: 1,
    flexDirection: 'row', alignItems: 'center', gap: spacing.md,
    padding: spacing.base, borderRadius: radius.lg, borderWidth: 1,
  },
  statIcon: {
    width: 36, height: 36, borderRadius: radius.md,
    alignItems: 'center', justifyContent: 'center',
  },
  statValue: {
    fontSize: typography.xl, fontWeight: typography.black,
    letterSpacing: -0.5, lineHeight: typography.xl + 2,
  },
  statSuffix: { fontSize: typography.md, fontWeight: typography.bold },
  statLabel: { fontSize: typography.xs, fontWeight: typography.bold, marginTop: 1 },

  // Cert stat card (con ribbon decorativo de fondo)
  certsCard: {
    flexBasis: '48%',
    flexGrow: 1,
    minHeight: 130,
    padding: spacing.base,
    borderRadius: radius.lg,
    borderWidth: 1,
    overflow: 'hidden',
    position: 'relative',
    justifyContent: 'space-between',
  },
  certsDecor: {
    position: 'absolute',
    right: -20, bottom: -22,
    opacity: 0.12,
    transform: [{ rotate: '-12deg' }],
  },
  certsBadge: {
    width: 28, height: 28,
    borderRadius: 14,
    backgroundColor: colors.brand,
    alignItems: 'center', justifyContent: 'center',
    alignSelf: 'flex-start',
    ...shadows.brand,
    shadowOpacity: 0.40,
    shadowRadius: 8,
  },
  certsBody: {
    marginTop: spacing.sm,
  },
  certsNum: {
    fontSize: 38,
    fontWeight: typography.black,
    letterSpacing: -1.5,
    lineHeight: 40,
  },
  certsLabel: {
    fontSize: typography.xs,
    fontWeight: typography.black,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    marginTop: 2,
  },

  // Hours progress card (con barra animada + icono decor de fondo)
  hoursCard: {
    flexBasis: '48%', flexGrow: 1,
    minHeight: 130,
    padding: spacing.base,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.xs,
    overflow: 'hidden',
    position: 'relative',
    justifyContent: 'space-between',
  },
  hoursDecor: {
    position: 'absolute',
    right: -20, bottom: -22,
    opacity: 0.12,
    transform: [{ rotate: '-12deg' }],
  },
  hoursBadge: {
    width: 28, height: 28,
    borderRadius: 14,
    backgroundColor: '#A855F7',
    alignItems: 'center', justifyContent: 'center',
    alignSelf: 'flex-start',
    shadowColor: '#A855F7',
    shadowOpacity: 0.40,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  hoursBody: {
    marginTop: spacing.xs,
  },
  hoursValue: {
    fontSize: typography.xl,
    fontWeight: typography.black,
    letterSpacing: -0.5,
    lineHeight: typography.xl + 2,
  },
  hoursSuffix: {
    fontSize: typography.md,
    fontWeight: typography.bold,
  },
  hoursLabel: {
    fontSize: typography.xs,
    fontWeight: typography.bold,
    marginTop: 1,
  },
  hoursBarTrack: {
    height: 8,
    borderRadius: 4,
    backgroundColor: 'rgba(168,85,247,0.12)',
    overflow: 'hidden',
    marginTop: 2,
  },
  hoursBarFillWrap: {
    height: '100%',
    borderRadius: 4,
    overflow: 'hidden',
    shadowColor: '#A855F7',
    shadowOpacity: 0.55,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 0 },
  },
  hoursBarFill: { flex: 1, borderRadius: 4 },
  hoursMetaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 2,
  },
  hoursMetaText: {
    fontSize: typography.xs - 1,
    fontWeight: typography.bold,
    letterSpacing: 0.3,
  },

  // Próximo evento card
  nextHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  nextTitle: {
    fontSize: typography.lg, fontWeight: typography.black,
    letterSpacing: -0.3, marginTop: spacing.sm,
    lineHeight: typography.lg * 1.2,
  },
  nextMeta: { flexDirection: 'row', gap: spacing.md, marginTop: spacing.xs },
  nextMetaItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  nextMetaText: { fontSize: typography.sm, fontWeight: typography.medium },

  countdownPill: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    alignSelf: 'flex-start',
    paddingHorizontal: spacing.md, paddingVertical: spacing.xs,
    borderRadius: radius.full,
    backgroundColor: 'rgba(245,136,48,0.12)',
    borderWidth: 1,
    borderColor: 'rgba(245,136,48,0.28)',
    marginTop: spacing.base,
  },
  countdownText: {
    fontSize: typography.sm, fontWeight: typography.black,
    letterSpacing: 0.2,
  },

  meetBtn: {
    flexDirection: 'row', alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.sm,
    marginTop: spacing.base,
    // Sin background, sin border — solo contenido dentro del GlassCard
  },
  meetText: {
    fontSize: typography.base, fontWeight: typography.black,
    letterSpacing: -0.1,
  },
  meetSub: {
    fontSize: typography.xs, fontWeight: typography.medium,
    marginTop: 1,
  },
  meetGo: {
    width: 32, height: 32,
    borderRadius: radius.full,
    backgroundColor: '#00832D',
    alignItems: 'center', justifyContent: 'center',
    ...shadows.sm,
  },

  // Sections
  section: { marginTop: spacing.xl, paddingHorizontal: spacing.xl },
  sectionHead: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    marginBottom: spacing.sm,
  },
  sectionTitle: {
    fontSize: typography.xs, fontWeight: typography.black,
    letterSpacing: 1.5, textTransform: 'uppercase',
  },
  sectionAction: {
    fontSize: typography.xs, fontWeight: typography.black,
    letterSpacing: 0.5, color: colors.brand,
  },

  // Sesion row (lista compacta)
  rowTop: { flexDirection: 'row' },
  rowTitle: {
    fontSize: typography.base, fontWeight: typography.black,
    letterSpacing: -0.2, marginTop: spacing.xs,
  },
  rowMeta: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: spacing.xs },
  rowMetaText: { fontSize: typography.sm, fontWeight: typography.medium },

  // Recomendados — carrusel horizontal estilo Amazon
  recosBlock: { marginTop: spacing.xl },
  recosCarousel: {
    paddingHorizontal: spacing.xl,
    gap: spacing.sm,
    paddingTop: spacing.sm,
  },
  recoCard: {
    width: RECO_CARD_W,
    borderRadius: radius.lg,
    borderWidth: 1,
    overflow: 'hidden',
    shadowColor: '#0F172A',
    shadowOpacity: 0.08,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  recoHero: {
    height: 100,
    width: '100%',
    position: 'relative',
    overflow: 'hidden',
  },
  recoDecor: {
    position: 'absolute',
    right: -8, bottom: -8,
  },
  recoModPill: {
    position: 'absolute',
    top: 8, left: 8,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 7,
    paddingVertical: 3,
    borderRadius: radius.full,
    backgroundColor: 'rgba(0,0,0,0.40)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.30)',
  },
  recoModText: {
    color: '#FFFFFF',
    fontSize: 9,
    fontWeight: typography.black,
    letterSpacing: 0.4,
  },
  recoDateBlock: {
    position: 'absolute',
    bottom: 8, left: 8,
    minWidth: 38,
    paddingVertical: 4,
    paddingHorizontal: 7,
    borderRadius: radius.md,
    backgroundColor: 'rgba(255,255,255,0.96)',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.20,
    shadowRadius: 5,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  recoDateDay: {
    fontSize: 15,
    fontWeight: typography.black,
    color: '#0F172A',
    letterSpacing: -0.5,
    lineHeight: 17,
  },
  recoDateMonth: {
    fontSize: 9,
    fontWeight: typography.black,
    color: colors.brand,
    letterSpacing: 0.8,
    marginTop: -1,
  },
  recoBody: {
    padding: spacing.sm,
    gap: 4,
  },
  recoTitle: {
    fontSize: typography.sm,
    fontWeight: typography.black,
    letterSpacing: -0.2,
    lineHeight: typography.sm * 1.25,
    minHeight: typography.sm * 1.25 * 2,
  },
  recoMetaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    marginTop: 2,
  },
  recoMeta: {
    fontSize: typography.xs,
    fontWeight: typography.medium,
    flex: 1,
  },

  // Certificados — carrusel horizontal
  certsBlock: { marginTop: spacing.xl },
  certsCarousel: {
    paddingHorizontal: spacing.xl,
    gap: spacing.sm,
    paddingTop: spacing.sm,
  },
  certCard: {
    width: CERT_CARD_W,
    height: CERT_CARD_H,
    borderRadius: radius.xl,
    overflow: 'hidden',
    ...shadows.brand,
  },
  certCardInner: {
    flex: 1,
    padding: spacing.base,
    position: 'relative',
    overflow: 'hidden',
  },
  certDecor: {
    position: 'absolute',
    right: -28, bottom: -28,
  },
  certTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  certHoursPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radius.full,
    backgroundColor: 'rgba(0,0,0,0.20)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.30)',
  },
  certHoursText: {
    color: '#FFFFFF',
    fontSize: typography.xs,
    fontWeight: typography.black,
    letterSpacing: 0.3,
  },
  certDownloadCircle: {
    width: 30, height: 30,
    borderRadius: 15,
    backgroundColor: 'rgba(255,255,255,0.20)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.35)',
    alignItems: 'center', justifyContent: 'center',
  },
  certMedalWrap: {
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  certMedal: {
    width: 64, height: 64,
    borderRadius: 32,
    backgroundColor: '#FFFFFF',
    alignItems: 'center', justifyContent: 'center',
    borderWidth: 3,
    borderColor: 'rgba(255,255,255,0.50)',
    ...shadows.lg,
  },
  certEyebrow: {
    fontSize: typography.xs - 2,
    fontWeight: typography.black,
    letterSpacing: 1.5,
    color: 'rgba(255,255,255,0.85)',
  },
  certTitleBig: {
    color: '#FFFFFF',
    fontSize: typography.base,
    fontWeight: typography.black,
    letterSpacing: -0.3,
    lineHeight: typography.base * 1.2,
    marginTop: 2,
  },
  certDate: {
    color: 'rgba(255,255,255,0.85)',
    fontSize: typography.xs,
    fontWeight: typography.bold,
    marginTop: 6,
  },
});
