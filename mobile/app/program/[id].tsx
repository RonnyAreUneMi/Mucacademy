import { useCallback, useEffect, useState } from 'react';
import {
  Image, Pressable, ScrollView, StyleSheet, Text, View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';

import { api } from '@/api/client';
import {
  brandScale, colors, radius, spacing, themed, typography,
} from '@/theme/tokens';
import { useTheme } from '@/stores/theme';
import { Badge, Button, Loader, NeuCard, RichText, stripHtml, useToast } from '@/components/ui';

type Seminar = {
  id: number;
  title: string;
  description: string;
  hours: number | null;
  date: string | null;
  modality: string;
  banner_url: string | null;
  skill: string | null;
  min_grade: number | null;
};
type ProgramDetail = {
  id: number;
  name: string;
  description: string;
  faculty: string;
  banner_url: string | null;
  course_count: number;
  total_hours: number;
  min_grade: number | null;
  seminars: Seminar[];
};

export default function ProgramDetailScreen() {
  const { id, inscrito: inscritoParam } = useLocalSearchParams<{ id: string; inscrito?: string }>();
  const [data, setData] = useState<ProgramDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [inscrito, setInscrito] = useState(inscritoParam === '1');
  const insets = useSafeAreaInsets();
  const theme = useTheme();
  const t = themed(theme);
  const toast = useToast();

  const load = useCallback(async () => {
    try {
      const res = await api.get<ProgramDetail>(`/api/v1/public/programs/${id}/`);
      setData(res);
    } catch (e: any) {
      toast.error(e?.message ?? 'No pudimos cargar el programa.', 'Error');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  async function inscribir() {
    setSubmitting(true);
    try {
      await api.post(`/api/v1/public/account/programs/${id}/enroll/`);
      setInscrito(true);
      toast.success('Quedaste inscrito en todos sus seminarios.', '¡Listo!');
    } catch (e: any) {
      toast.error(e?.message ?? 'No pudimos inscribirte.', 'Error');
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <View style={[styles.safe, { backgroundColor: t.bg }]}>
        <View style={styles.loading}><Loader size={88} /></View>
      </View>
    );
  }
  if (!data) return null;

  const tieneDescripcion = !!stripHtml(data.description);

  return (
    <View style={[styles.safe, { backgroundColor: t.bg }]}>
      <ScrollView
        contentContainerStyle={{ paddingBottom: 120 + insets.bottom }}
        showsVerticalScrollIndicator={false}
      >
        {/* HERO */}
        <View style={styles.hero}>
          {data.banner_url ? (
            <Image source={{ uri: data.banner_url }} style={StyleSheet.absoluteFillObject} resizeMode="cover" />
          ) : (
            <LinearGradient
              colors={['#162054', '#1E2F6B', brandScale[700]] as [string, string, string]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
              style={StyleSheet.absoluteFillObject}
            />
          )}
          <LinearGradient
            colors={['rgba(0,0,0,0.15)', 'rgba(0,0,0,0.72)'] as [string, string]}
            style={StyleSheet.absoluteFillObject}
          />

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

          <View style={styles.heroContent}>
            <View style={{ flexDirection: 'row', gap: spacing.xs }}>
              <Badge
                tone="navy"
                variant="solid"
                size="md"
                iconLeft={<Ionicons name="layers" size={12} color="#FFFFFF" />}
              >
                Programa
              </Badge>
              {inscrito ? (
                <Badge tone="success" variant="soft" size="md" dot>Inscrito</Badge>
              ) : null}
            </View>
            <Text style={styles.heroTitle}>{data.name}</Text>
          </View>
        </View>

        {/* STATS */}
        <View style={styles.statsRow}>
          <StatBox theme={theme} value={String(data.course_count)} label="Seminarios" />
          <StatBox theme={theme} value={`${data.total_hours}h`} label="Horas" />
          <StatBox
            theme={theme}
            value={data.min_grade ? String(data.min_grade) : '—'}
            label="Nota mínima"
            highlight={!!data.min_grade}
          />
        </View>

        {/* NOTA MÍNIMA */}
        {data.min_grade ? (
          <View style={styles.section}>
            <View style={[styles.gradeNote, { borderColor: 'rgba(245,136,48,0.25)' }]}>
              <Ionicons name="ribbon" size={16} color={colors.brand} style={{ marginTop: 1 }} />
              <Text style={[styles.gradeNoteText, { color: t.textMuted }]}>
                Para el certificado del programa necesitás aprobar la evaluación de{' '}
                <Text style={{ fontWeight: typography.black, color: t.text }}>cada seminario</Text> con
                al menos <Text style={{ fontWeight: typography.black, color: t.text }}>{data.min_grade}/100</Text>.
              </Text>
            </View>
          </View>
        ) : null}

        {/* DESCRIPCIÓN */}
        {tieneDescripcion ? (
          <View style={styles.section}>
            <Text style={[styles.sectionLabel, { color: t.textMuted }]}>SOBRE EL PROGRAMA</Text>
            <RichText html={data.description} />
          </View>
        ) : null}

        {/* SEMINARIOS */}
        <View style={styles.section}>
          <Text style={[styles.sectionLabel, { color: t.textMuted }]}>
            SEMINARIOS DEL PROGRAMA
          </Text>
          <View style={{ gap: spacing.sm }}>
            {data.seminars.map((s, i) => (
              <Pressable
                key={s.id}
                onPress={() => router.push({ pathname: '/event/[id]', params: { id: String(s.id) } })}
                style={({ pressed }) => pressed && { opacity: 0.9, transform: [{ scale: 0.99 }] }}
              >
                <NeuCard style={styles.semCard}>
                  <View style={styles.semImgWrap}>
                    {s.banner_url ? (
                      <Image source={{ uri: s.banner_url }} style={StyleSheet.absoluteFillObject} resizeMode="cover" />
                    ) : (
                      <LinearGradient
                        colors={[brandScale[500], brandScale[700]] as [string, string]}
                        style={StyleSheet.absoluteFillObject}
                      />
                    )}
                    <View style={styles.semNum}>
                      <Text style={styles.semNumText}>{i + 1}</Text>
                    </View>
                  </View>
                  <View style={styles.semBody}>
                    <Text style={[styles.semTitle, { color: t.text }]} numberOfLines={2}>{s.title}</Text>
                    {s.description ? (
                      <Text style={[styles.semDesc, { color: t.textMuted }]} numberOfLines={2}>
                        {stripHtml(s.description)}
                      </Text>
                    ) : null}
                    <View style={styles.semMetaRow}>
                      {s.skill ? (
                        <View style={styles.semChip}>
                          <Ionicons name="flash" size={9} color={colors.brand} />
                          <Text style={styles.semChipText}>{s.skill}</Text>
                        </View>
                      ) : null}
                      {s.hours ? (
                        <Text style={[styles.semMeta, { color: t.textMuted }]}>{s.hours}h</Text>
                      ) : null}
                      {s.min_grade ? (
                        <Text style={[styles.semMeta, { color: colors.brand }]}>
                          Aprobás con {s.min_grade}
                        </Text>
                      ) : null}
                    </View>
                  </View>
                  <View style={styles.semChevron}>
                    <Ionicons name="chevron-forward" size={16} color={t.textMuted} />
                  </View>
                </NeuCard>
              </Pressable>
            ))}
          </View>
        </View>
      </ScrollView>

      {/* CTA fijo */}
      <View style={[styles.ctaBar, { backgroundColor: t.card, borderColor: t.border, paddingBottom: insets.bottom + spacing.sm }]}>
        {inscrito ? (
          <View style={styles.ctaInscrito}>
            <Ionicons name="checkmark-circle" size={18} color={colors.success} />
            <Text style={[styles.ctaInscritoText, { color: t.text }]}>Ya estás inscrito en este programa</Text>
          </View>
        ) : (
          <Button
            variant="filled"
            tone="brand"
            onPress={inscribir}
            disabled={submitting}
            iconLeft={<Ionicons name="bookmark" size={16} color="#FFFFFF" />}
          >
            {submitting ? 'Inscribiendo…' : 'Inscribirme al programa'}
          </Button>
        )}
      </View>
    </View>
  );
}

function StatBox({
  theme, value, label, highlight,
}: { theme: 'light' | 'dark'; value: string; label: string; highlight?: boolean }) {
  const t = themed(theme);
  return (
    <View style={[styles.statBox, { backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(15,23,42,0.04)' }]}>
      <Text style={[styles.statValue, { color: highlight ? colors.brand : t.text }]}>{value}</Text>
      <Text style={[styles.statLabel, { color: t.textMuted }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },

  hero: { height: 240, width: '100%', position: 'relative', justifyContent: 'flex-end' },
  backBtn: {
    position: 'absolute', left: spacing.base,
    width: 38, height: 38, borderRadius: 19,
    alignItems: 'center', justifyContent: 'center',
    backgroundColor: 'rgba(0,0,0,0.35)',
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.25)',
  },
  heroContent: { padding: spacing.base, gap: spacing.sm },
  heroTitle: {
    color: '#FFFFFF',
    fontSize: typography.xxl,
    fontWeight: typography.black,
    letterSpacing: -0.5,
  },

  statsRow: {
    flexDirection: 'row', gap: spacing.sm,
    paddingHorizontal: spacing.base, marginTop: spacing.base,
  },
  statBox: {
    flex: 1, borderRadius: radius.lg,
    paddingVertical: spacing.sm, alignItems: 'center',
  },
  statValue: { fontSize: typography.xl, fontWeight: typography.black, letterSpacing: -0.5 },
  statLabel: { fontSize: 10, fontWeight: typography.bold, textTransform: 'uppercase', letterSpacing: 0.4, marginTop: 2 },

  section: { paddingHorizontal: spacing.base, marginTop: spacing.lg },
  sectionLabel: {
    fontSize: typography.xs, fontWeight: typography.black,
    letterSpacing: 0.6, marginBottom: spacing.sm,
  },
  gradeNote: {
    flexDirection: 'row', gap: spacing.sm,
    padding: spacing.sm + 2, borderRadius: radius.lg, borderWidth: 1,
    backgroundColor: 'rgba(245,136,48,0.07)',
  },
  gradeNoteText: { flex: 1, fontSize: typography.sm, lineHeight: typography.sm * 1.5 },

  descText: { fontSize: typography.sm, lineHeight: typography.sm * 1.55 },

  semCard: { flexDirection: 'row', padding: 0, overflow: 'hidden' },
  semImgWrap: { width: 96, height: 96, position: 'relative' },
  semNum: {
    position: 'absolute', top: 6, left: 6,
    width: 22, height: 22, borderRadius: 11,
    backgroundColor: 'rgba(255,255,255,0.92)',
    alignItems: 'center', justifyContent: 'center',
  },
  semNumText: { fontSize: 12, fontWeight: typography.black, color: colors.brand },
  semBody: { flex: 1, padding: spacing.sm, gap: 3, justifyContent: 'center' },
  semChevron: { alignSelf: 'center', paddingRight: spacing.sm, paddingLeft: 2 },
  semTitle: { fontSize: typography.sm + 1, fontWeight: typography.black, letterSpacing: -0.2 },
  semDesc: { fontSize: typography.xs, lineHeight: typography.xs * 1.4 },
  semMetaRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, marginTop: 2, flexWrap: 'wrap' },
  semChip: {
    flexDirection: 'row', alignItems: 'center', gap: 3,
    paddingHorizontal: 6, paddingVertical: 2, borderRadius: radius.sm,
    backgroundColor: 'rgba(245,136,48,0.12)',
  },
  semChipText: { fontSize: 10, fontWeight: typography.black, color: colors.brand },
  semMeta: { fontSize: typography.xs, fontWeight: typography.bold },

  ctaBar: {
    position: 'absolute', left: 0, right: 0, bottom: 0,
    paddingHorizontal: spacing.base, paddingTop: spacing.sm,
    borderTopWidth: 1,
  },
  ctaInscrito: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: spacing.xs,
    paddingVertical: spacing.sm,
  },
  ctaInscritoText: { fontSize: typography.sm, fontWeight: typography.bold },
});
