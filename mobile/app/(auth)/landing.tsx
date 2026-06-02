import { useEffect, useState } from 'react';
import {
  Linking, Pressable, ScrollView, StyleSheet, Text, View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';

import { api } from '@/api/client';
import {
  brandScale, colors, radius, shadows, spacing, themed, typography,
} from '@/theme/tokens';
import { useTheme } from '@/stores/theme';
import {
  Badge, BrandLogo, Button, Carousel, GradientText, NeuCard, VBackground,
} from '@/components/ui';

type EventHero = {
  id: number;
  titulo_display: string;
  date: string;
  day_of_week: string;
  start_time: string;
  end_time: string;
  es_virtual: boolean;
  location: string;
  banner_url: string | null;
};
type LandingResponse = {
  eventos_hero: EventHero[];
  stats: {
    total_certificados: number;
    total_eventos: number;
    total_horas: number;
    total_participantes: number;
  };
};

export default function LandingScreen() {
  const [data, setData] = useState<LandingResponse | null>(null);
  const theme = useTheme();
  const t = themed(theme);

  useEffect(() => {
    api.get<LandingResponse>('/api/v1/public/account/landing/')
      .then(setData)
      .catch(() => {});
  }, []);

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: t.bg }]} edges={['top']}>
      <VBackground intensity={theme === 'dark' ? 0.7 : 0.85} />

      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        {/* Top bar — solo brand a la izquierda */}
        <View style={styles.topBar}>
          <BrandLogo size={22} />
          <Pressable
            onPress={() => router.push('/(auth)/login')}
            style={({ pressed }) => [styles.topLink, pressed && { opacity: 0.6 }]}
            hitSlop={8}
          >
            <Text style={[styles.topLinkText, { color: t.textMuted }]}>Iniciar sesión</Text>
          </Pressable>
        </View>

        {/* HERO */}
        <View style={styles.hero}>
          <View style={[styles.eyebrow, { backgroundColor: 'rgba(245,136,48,0.12)', borderColor: 'rgba(245,136,48,0.28)' }]}>
            <Ionicons name="sparkles" size={11} color={colors.brand} />
            <Text style={styles.eyebrowText}>SISTEMA DE CERTIFICACIÓN · UNEMI</Text>
          </View>

          <View style={styles.heroTitleWrap}>
            <Text style={[styles.heroTitle, { color: t.text }]}>
              Certifica, aprende,
            </Text>
            <View style={styles.heroTitleSecondLine}>
              <GradientText style={styles.heroTitle}>verifica</GradientText>
              <Text style={[styles.heroTitle, { color: t.text }]}> — todo con IA.</Text>
            </View>
          </View>

          <Text style={[styles.heroSubtitle, { color: t.textMuted }]}>
            Tus diplomas siempre disponibles. Los eventos académicos te encuentran.
            La IA te resume las reuniones y te recomienda qué seguir.
          </Text>

          <View style={styles.ctas}>
            <Button
              tone="brand"
              variant="filled"
              size="lg"
              fullWidth
              onPress={() => router.push('/(auth)/register')}
              iconRight={<Ionicons name="arrow-forward" size={16} color="#FFFFFF" />}
            >
              Crear cuenta gratis
            </Button>
            <Button
              tone="brand"
              variant="outline"
              size="lg"
              fullWidth
              onPress={() => router.push('/(auth)/login')}
              iconLeft={<Ionicons name="log-in-outline" size={18} color={colors.brand} />}
            >
              Ya tengo cuenta
            </Button>
          </View>

          {/* Trust strip */}
          <View style={styles.trust}>
            <TrustChip icon="shield-checkmark" label="Diplomas auténticos" />
            <TrustChip icon="flash"           label="Sin instalación" />
            <TrustChip icon="phone-portrait"  label="iOS y Android" />
          </View>
        </View>

        {/* SEARCH BAR — verificar certificado */}
        <View style={styles.section}>
          <Pressable
            onPress={() => Linking.openURL(`${api.baseUrl}/buscar/`)}
            style={({ pressed }) => [
              styles.searchBar,
              {
                backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.06)' : '#FFFFFF',
                borderColor: t.border,
              },
              pressed && { opacity: 0.85 },
            ]}
          >
            <View style={[styles.searchIconBox, { backgroundColor: colors.brand }]}>
              <Ionicons name="shield-checkmark" size={16} color="#FFFFFF" />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={[styles.searchTitle, { color: t.text }]}>Verificar un certificado</Text>
              <Text style={[styles.searchSub, { color: t.textMuted }]}>
                Cédula, nombre o código del diploma
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color={t.textMuted} />
          </Pressable>
        </View>

        {/* CARRUSEL DE EVENTOS DESTACADOS */}
        {data?.eventos_hero?.length ? (
          <View style={styles.section}>
            <View style={styles.sectionHead}>
              <View style={[styles.eyebrow, { backgroundColor: 'rgba(245,136,48,0.12)', borderColor: 'rgba(245,136,48,0.28)' }]}>
                <Ionicons name="flash" size={11} color={colors.brand} />
                <Text style={styles.eyebrowText}>EN VIVO · PRÓXIMOS</Text>
              </View>
              <Text style={[styles.sectionTitle, { color: t.text }]}>Eventos destacados</Text>
              <Text style={[styles.sectionSub, { color: t.textMuted }]}>
                Regístrate sin necesidad de cuenta. Pero con cuenta los sigues todos.
              </Text>
            </View>

            <Carousel
              data={data.eventos_hero}
              itemHeight={260}
              renderItem={(e) => <HeroSlide evento={e} />}
            />
          </View>
        ) : null}

        {/* FEATURES — bento cards (mirror del #features del web) */}
        <View style={[styles.section, { paddingHorizontal: spacing.xl }]}>
          <View style={[styles.eyebrow, { backgroundColor: 'rgba(245,136,48,0.12)', borderColor: 'rgba(245,136,48,0.28)' }]}>
            <Ionicons name="hardware-chip" size={11} color={colors.brand} />
            <Text style={styles.eyebrowText}>IA AL SERVICIO DEL APRENDIZAJE</Text>
          </View>
          <Text style={[styles.sectionTitle, { color: t.text, marginTop: spacing.sm }]}>
            Más que un certificado.
          </Text>
          <Text style={[styles.sectionSub, { color: t.textMuted }]}>
            Una experiencia completa de inicio a fin.
          </Text>

          <View style={styles.featuresGrid}>
            <FeatureCard
              icon="sparkles"
              title="Resúmenes con IA"
              text="Conectamos con Google Meet, transcribimos las charlas y la IA prepara un resumen estructurado al terminar el evento."
              gradient={[brandScale[500], brandScale[700]] as [string, string]}
            />
            <FeatureCard
              icon="list"
              title="Cuestionarios automáticos"
              text="La IA crea preguntas de comprensión a partir del contenido del evento."
              gradient={['#162054', '#0C1335'] as [string, string]}
            />
            <FeatureCard
              icon="shield-checkmark"
              title="Verificación pública"
              text="Cada certificado lleva un código único. Comprobás su autenticidad sin cuenta."
              gradient={['#1E40AF', '#1E3A8A'] as [string, string]}
            />
            <FeatureCard
              icon="qr-code"
              title="Asistencia con QR"
              text="Escaneá el QR del evento, confirmás tu asistencia y queda registrada. Sin papel."
              gradient={['#F59E0B', '#D97706'] as [string, string]}
            />
          </View>
        </View>

        {/* PROCESO — 4 pasos (mirror del #proceso del web) */}
        <View style={[styles.section, { paddingHorizontal: spacing.xl }]}>
          <View style={[styles.eyebrow, { backgroundColor: 'rgba(245,136,48,0.12)', borderColor: 'rgba(245,136,48,0.28)' }]}>
            <Ionicons name="trail-sign" size={11} color={colors.brand} />
            <Text style={styles.eyebrowText}>CÓMO FUNCIONA</Text>
          </View>
          <Text style={[styles.sectionTitle, { color: t.text, marginTop: spacing.sm }]}>
            De la invitación al diploma.
          </Text>
          <Text style={[styles.sectionSub, { color: t.textMuted }]}>
            En 4 pasos. Vos te enfocás en aprender, nosotros del resto.
          </Text>

          <Stepper
            steps={[
              { title: 'Te inscribís',           text: 'Buscás un evento que te interese y te inscribís con un solo clic.' },
              { title: 'Asistís',                text: 'Recibís recordatorios. Acudís presencial o virtual; el QR / Meet registra tu asistencia.' },
              { title: 'Aprendés con IA',        text: 'Al terminar, la IA prepara el resumen y un cuestionario para repasar.' },
              { title: 'Recibís tu certificado', text: 'Diploma digital firmado, descargable y verificable públicamente.' },
            ]}
          />
        </View>

        {/* STATS */}
        {data?.stats ? (
          <View style={styles.statsRow}>
            <StatPill value={data.stats.total_certificados} label="Certificados" />
            <StatPill value={data.stats.total_eventos}      label="Eventos" />
            <StatPill value={`${data.stats.total_horas}h`}  label="Horas" />
          </View>
        ) : null}

        {/* CTA final */}
        <View style={[styles.section, { paddingHorizontal: spacing.xl, marginTop: spacing.xl }]}>
          <NeuCard padded>
            <View style={{ alignItems: 'center' }}>
              <Badge tone="brand" variant="soft" size="md" iconLeft={<Ionicons name="rocket" size={11} color={colors.brand} />}>
                Empezá hoy
              </Badge>
              <Text style={[styles.ctaTitle, { color: t.text }]}>
                Tu próximo certificado, en{' '}
                <Text style={{ color: colors.brand }}>2 minutos</Text>.
              </Text>
              <Text style={[styles.ctaSub, { color: t.textMuted }]}>
                Sin tarjeta. Sin instalación. Cancelás cuando quieras.
              </Text>
              <View style={{ marginTop: spacing.base, alignSelf: 'stretch' }}>
                <Button
                  tone="brand"
                  variant="filled"
                  size="lg"
                  fullWidth
                  onPress={() => router.push('/(auth)/register')}
                  iconRight={<Ionicons name="arrow-forward" size={16} color="#FFFFFF" />}
                >
                  Crear mi cuenta
                </Button>
              </View>
            </View>
          </NeuCard>
        </View>

        <Text style={[styles.footer, { color: t.textMuted }]}>certifai · UNEMI · 2026</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

// ── Subcomponentes ────────────────────────────────────────────────

function TrustChip({ icon, label }: {
  icon: React.ComponentProps<typeof Ionicons>['name']; label: string;
}) {
  const t = themed(useTheme());
  return (
    <View style={styles.trustChip}>
      <Ionicons name={icon} size={12} color={colors.brand} />
      <Text style={[styles.trustText, { color: t.textMuted }]}>{label}</Text>
    </View>
  );
}

function StatPill({ value, label }: { value: string | number; label: string }) {
  const t = themed(useTheme());
  return (
    <View style={[styles.statPill, { borderColor: t.border, backgroundColor: 'rgba(245,136,48,0.06)' }]}>
      <Text style={[styles.statValue, { color: colors.brand }]}>{value}</Text>
      <Text style={[styles.statLabel, { color: t.textMuted }]}>{label}</Text>
    </View>
  );
}

function FeatureCard({
  icon, title, text, gradient,
}: {
  icon: React.ComponentProps<typeof Ionicons>['name'];
  title: string;
  text: string;
  gradient: [string, string];
}) {
  const t = themed(useTheme());
  return (
    <View style={[
      styles.feature,
      { backgroundColor: t.cardSoft, borderColor: t.border },
      shadows.sm,
    ]}>
      <View style={styles.featureIconWrap}>
        <LinearGradient
          colors={gradient}
          start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
          style={styles.featureIconGradient}
        >
          <Ionicons name={icon} size={18} color="#FFFFFF" />
        </LinearGradient>
      </View>
      <Text style={[styles.featureTitle, { color: t.text }]}>{title}</Text>
      <Text style={[styles.featureText, { color: t.textMuted }]}>{text}</Text>
    </View>
  );
}

function Stepper({ steps }: { steps: { title: string; text: string }[] }) {
  const t = themed(useTheme());
  const lineColor = useTheme() === 'dark' ? 'rgba(245,136,48,0.35)' : brandScale[200];

  return (
    <View style={styles.stepper}>
      {/* Línea vertical continua detrás de los badges */}
      <View
        style={[
          styles.stepperLine,
          { backgroundColor: lineColor },
        ]}
      />

      {steps.map((step, i) => (
        <View key={i} style={styles.stepRow}>
          <View style={[styles.stepBadge, { backgroundColor: colors.brand }, shadows.brand]}>
            <Text style={styles.stepBadgeText}>{i + 1}</Text>
          </View>
          <View style={styles.stepBody}>
            <Text style={[styles.stepTitle, { color: t.text }]}>{step.title}</Text>
            <Text style={[styles.stepText, { color: t.textMuted }]}>{step.text}</Text>
          </View>
        </View>
      ))}
    </View>
  );
}

function HeroSlide({ evento }: { evento: EventHero }) {
  const formattedDate = formatDate(evento.date);
  const horaInicio = evento.start_time.slice(0, 5);
  const horaFin = evento.end_time.slice(0, 5);

  return (
    <View style={styles.slide}>
      <LinearGradient
        colors={evento.es_virtual
          ? ['#1E3A8A', '#1E40AF', '#0F1F4D'] as [string, string, string]
          : [brandScale[500], '#E8721C', brandScale[700]] as [string, string, string]
        }
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={StyleSheet.absoluteFillObject}
      />
      <LinearGradient
        colors={['transparent', 'rgba(0,0,0,0.6)'] as [string, string]}
        style={StyleSheet.absoluteFillObject}
      />
      <View style={styles.slideDecor}>
        <Ionicons
          name={evento.es_virtual ? 'videocam' : 'business'}
          size={140}
          color="rgba(255,255,255,0.10)"
        />
      </View>

      <View style={styles.slideContent}>
        <Badge
          tone={evento.es_virtual ? 'info' : 'brand'}
          variant="solid"
          size="sm"
          iconLeft={
            <Ionicons
              name={evento.es_virtual ? 'videocam' : 'business'}
              size={11}
              color="#FFFFFF"
            />
          }
        >
          {evento.es_virtual ? 'Virtual' : 'Presencial'}
        </Badge>

        <Text style={styles.slideTitle} numberOfLines={2}>
          {evento.titulo_display}
        </Text>

        <View style={styles.slideMeta}>
          <View style={styles.slideMetaItem}>
            <Ionicons name="calendar" size={13} color={colors.brand} />
            <Text style={styles.slideMetaText}>{formattedDate}</Text>
          </View>
          <View style={styles.slideMetaItem}>
            <Ionicons name="time" size={13} color={colors.brand} />
            <Text style={styles.slideMetaText}>{horaInicio}–{horaFin}</Text>
          </View>
        </View>

        {evento.location && !evento.es_virtual ? (
          <View style={styles.slideMetaItem}>
            <Ionicons name="location" size={13} color={colors.brand} />
            <Text style={styles.slideMetaText} numberOfLines={1}>{evento.location}</Text>
          </View>
        ) : null}
      </View>
    </View>
  );
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso + 'T00:00:00');
    return d.toLocaleDateString('es-EC', { day: '2-digit', month: 'short' });
  } catch {
    return iso;
  }
}

// ── Estilos ───────────────────────────────────────────────────────
const styles = StyleSheet.create({
  safe:   { flex: 1 },
  scroll: { paddingBottom: spacing.huge },

  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.sm,
    paddingBottom: spacing.lg,
  },
  topLink: { paddingHorizontal: spacing.sm, paddingVertical: 4 },
  topLinkText: { fontSize: typography.sm, fontWeight: typography.bold },

  hero: { paddingHorizontal: spacing.xl, marginBottom: spacing.xl },
  eyebrow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: radius.full,
    alignSelf: 'flex-start',
    borderWidth: 1,
  },
  eyebrowText: {
    fontSize: typography.xs,
    fontWeight: typography.black,
    color: colors.brand,
    letterSpacing: 1.2,
  },
  heroTitleWrap: { marginTop: spacing.lg },
  heroTitleSecondLine: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'baseline' },
  heroTitle: {
    fontSize: 36,
    fontWeight: typography.black,
    letterSpacing: -1,
    lineHeight: 40,
  },
  heroSubtitle: {
    fontSize: typography.base,
    lineHeight: typography.base * 1.5,
    marginTop: spacing.base,
  },
  ctas: { gap: spacing.sm, marginTop: spacing.xl },

  trust: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    marginTop: spacing.lg,
  },
  trustChip: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  trustText: { fontSize: typography.xs, fontWeight: typography.bold },

  section: { marginTop: spacing.xl },
  sectionHead: { paddingHorizontal: spacing.xl, marginBottom: spacing.base },
  sectionTitle: {
    fontSize: typography.xl,
    fontWeight: typography.black,
    letterSpacing: -0.4,
    marginTop: spacing.sm,
  },
  sectionSub: {
    fontSize: typography.sm,
    marginTop: 2,
    lineHeight: typography.sm * 1.5,
  },

  // Search bar
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    marginHorizontal: spacing.xl,
    padding: spacing.base,
    borderRadius: radius.lg,
    borderWidth: 1,
    ...shadows.sm,
  },
  searchIconBox: {
    width: 36, height: 36,
    borderRadius: radius.md,
    alignItems: 'center', justifyContent: 'center',
    ...shadows.brand,
  },
  searchTitle: { fontSize: typography.base, fontWeight: typography.black, letterSpacing: -0.2 },
  searchSub:   { fontSize: typography.xs, marginTop: 2 },

  // Slide
  slide: {
    flex: 1,
    borderRadius: radius.xl,
    overflow: 'hidden',
    ...shadows.md,
  },
  slideDecor: { position: 'absolute', right: -16, bottom: -10 },
  slideContent: {
    flex: 1,
    padding: spacing.lg,
    justifyContent: 'flex-end',
    gap: spacing.xs,
  },
  slideTitle: {
    color: '#FFFFFF',
    fontSize: typography.xl,
    fontWeight: typography.black,
    letterSpacing: -0.4,
    lineHeight: typography.xl * 1.15,
    marginTop: spacing.sm,
  },
  slideMeta: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    marginTop: spacing.xs,
  },
  slideMetaItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  slideMetaText: {
    color: 'rgba(255,255,255,0.92)',
    fontSize: typography.sm,
    fontWeight: typography.medium,
  },

  // Features
  featuresGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    marginTop: spacing.lg,
  },
  feature: {
    flexBasis: '48%',
    flexGrow: 1,
    padding: spacing.base,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.xs,
  },
  featureIconWrap: { marginBottom: spacing.xs },
  featureIconGradient: {
    width: 38, height: 38,
    borderRadius: radius.md,
    alignItems: 'center', justifyContent: 'center',
    ...shadows.sm,
  },
  featureTitle: {
    fontSize: typography.base,
    fontWeight: typography.black,
    letterSpacing: -0.2,
  },
  featureText: {
    fontSize: typography.sm,
    lineHeight: typography.sm * 1.45,
  },

  // Stepper (1→2→3→4 conectado con línea vertical)
  stepper: {
    marginTop: spacing.lg,
    position: 'relative',
  },
  stepperLine: {
    position: 'absolute',
    left: 19,                       // (badgeWidth=40 / 2) - (lineWidth=2 / 2) = 19
    top: 20,                        // empieza al centro del primer badge
    bottom: 20,                     // termina al centro del último badge
    width: 2,
    borderRadius: 1,
  },
  stepRow: {
    flexDirection: 'row',
    gap: spacing.md,
    paddingVertical: spacing.sm,
    alignItems: 'flex-start',
  },
  stepBadge: {
    width: 40, height: 40,
    borderRadius: radius.md,
    alignItems: 'center', justifyContent: 'center',
    // Pongo el badge SOBRE la línea con borderColor del bg para "tapar" el segmento detrás
    borderWidth: 3,
    borderColor: 'transparent',
    zIndex: 2,
  },
  stepBadgeText: {
    color: '#FFFFFF',
    fontSize: typography.md,
    fontWeight: typography.black,
  },
  stepBody: {
    flex: 1,
    paddingTop: 2,
  },
  stepTitle: {
    fontSize: typography.base,
    fontWeight: typography.black,
    letterSpacing: -0.2,
    marginBottom: 2,
  },
  stepText: {
    fontSize: typography.sm,
    lineHeight: typography.sm * 1.5,
  },

  // Stats
  statsRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    paddingHorizontal: spacing.xl,
    marginTop: spacing.xl,
  },
  statPill: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.sm,
    borderWidth: 1,
    borderRadius: radius.lg,
  },
  statValue: {
    fontSize: typography.xl,
    fontWeight: typography.black,
    letterSpacing: -0.5,
  },
  statLabel: {
    fontSize: typography.xs,
    fontWeight: typography.bold,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    marginTop: 2,
  },

  // CTA final
  ctaTitle: {
    fontSize: typography.lg,
    fontWeight: typography.black,
    letterSpacing: -0.3,
    textAlign: 'center',
    marginTop: spacing.sm,
  },
  ctaSub: {
    fontSize: typography.sm,
    textAlign: 'center',
    marginTop: 4,
    lineHeight: typography.sm * 1.45,
  },

  footer: {
    fontSize: typography.xs,
    textAlign: 'center',
    marginTop: spacing.xl,
    opacity: 0.6,
  },
});
