import { useEffect, useState } from 'react';
import {
  FlatList, Linking, Pressable,
  RefreshControl, StyleSheet, Text, TextInput, View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';

import { api } from '@/api/client';
import {
  brandScale, colors, radius, spacing, TAB_BAR_HEIGHT,
  themed, typography,
} from '@/theme/tokens';
import { useTheme } from '@/stores/theme';
import { Loader, NeuCard, ScreenHeader, VBackground } from '@/components/ui';

type Certificate = {
  id: number;
  course: string;
  course_date: string | null;
  hours: number;
  verification_hash: string;
  lote_nombre: string | null;
  is_program?: boolean;
  download_url: string;
  verify_url: string;
};

export default function CertificadosScreen() {
  const [data, setData]       = useState<Certificate[]>([]);
  const [count, setCount]     = useState(0);
  const [q, setQ]             = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const theme = useTheme();
  const t = themed(theme);

  async function load() {
    try {
      const params = q ? `?q=${encodeURIComponent(q)}` : '';
      const res = await api.get<{ count: number; results: Certificate[] }>(
        `/api/v1/public/account/certificates/${params}`
      );
      setData(res.results);
      setCount(res.count);
    } catch {
      // silencio
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => { load(); }, []);
  useEffect(() => {
    const tt = setTimeout(load, 300);
    return () => clearTimeout(tt);
  }, [q]);

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: t.bg }]}>
      <VBackground intensity={theme === 'dark' ? 0.5 : 0.25} variant="mixed" />
      <ScreenHeader
        eyebrow="MIS CERTIFICADOS"
        title={`${count} certificado${count === 1 ? '' : 's'}`}
        gradientTitle
        rightSlot={
          <Pressable
            onPress={() => router.push('/evaluation' as any)}
            style={({ pressed }) => [styles.evalBtn, pressed && { opacity: 0.7 }]}
            hitSlop={8}
          >
            <Ionicons name="clipboard-outline" size={16} color={colors.brand} />
            <Text style={styles.evalBtnText}>Evaluaciones</Text>
          </Pressable>
        }
      />
      <View style={[
        styles.searchWrap,
        {
          backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(15,23,42,0.04)',
          borderColor: t.border,
        },
      ]}>
        <Ionicons name="search" size={16} color={t.textMuted} style={{ marginLeft: spacing.md }} />
        <TextInput
          style={[styles.search, { color: t.text }]}
          value={q} onChangeText={setQ}
          placeholder="Buscar curso o lote…"
          placeholderTextColor={t.textMuted}
        />
      </View>

      {loading ? (
        <View style={styles.loading}><Loader size={88} /></View>
      ) : (
        <FlatList
          contentContainerStyle={{ padding: spacing.base, gap: spacing.sm, paddingBottom: TAB_BAR_HEIGHT + spacing.lg }}
          data={data}
          keyExtractor={(c) => String(c.id)}
          renderItem={({ item }) => <CertificadoCard cert={item} />}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => { setRefreshing(true); load(); }}
              tintColor={colors.brand}
            />
          }
          ListEmptyComponent={
            <View style={styles.empty}>
              <Text style={[styles.emptyText, { color: t.textMuted }]}>
                {q ? `Sin resultados para "${q}"` : 'Aún no tienes certificados.'}
              </Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}

function CertificadoCard({ cert }: { cert: Certificate }) {
  const t = themed(useTheme());
  const dateBlock = parseDateBlock(cert.course_date);
  const isProgram = !!cert.is_program;
  const gradientColors = isProgram
    ? (['#7C3AED', '#6D28D9', '#4C1D95'] as [string, string, string])
    : ([brandScale[400], brandScale[600], brandScale[700]] as [string, string, string]);

  function download() {
    Linking.openURL(`${api.baseUrl}${cert.download_url}`);
  }
  return (
    <NeuCard onPress={download} padded={false} style={styles.card}>
      {/* Preview tipo mini-diploma con gradiente brand */}
      <View style={styles.preview}>
        <LinearGradient
          colors={gradientColors}
          start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
          style={StyleSheet.absoluteFillObject}
        />
        {/* Decoración: ribbon grande translúcido al fondo */}
        <View style={styles.previewDecor}>
          <Ionicons name={isProgram ? 'school' : 'ribbon'} size={86} color="rgba(255,255,255,0.15)" />
        </View>
        {/* Watermark CERT / PROGRAMA */}
        <View style={styles.previewBadge}>
          <Ionicons name={isProgram ? 'git-network' : 'shield-checkmark'} size={11} color="#FFFFFF" />
          <Text style={styles.previewBadgeText}>{isProgram ? 'PROGRAMA' : 'CERTIFICADO'}</Text>
        </View>
        {/* Sello horas */}
        <View style={styles.previewSeal}>
          <Text style={styles.previewSealNum}>{cert.hours}</Text>
          <Text style={styles.previewSealLabel}>HORAS</Text>
        </View>
      </View>

      {/* Body: título + lote + fecha bloque a la derecha */}
      <View style={styles.body}>
        <View style={{ flex: 1 }}>
          <Text style={[styles.cardTitle, { color: t.text }]} numberOfLines={2}>
            {cert.course}
          </Text>
          {cert.lote_nombre ? (
            <Text style={[styles.cardLote, { color: t.textMuted }]} numberOfLines={1}>
              {cert.lote_nombre}
            </Text>
          ) : null}
          <View style={styles.cardFooter}>
            <Ionicons name="download-outline" size={14} color={colors.brand} />
            <Text style={[styles.cardCta, { color: colors.brand }]}>Descargar PDF</Text>
          </View>
        </View>

        {/* Bloque de fecha (día grande + mes + año) */}
        {dateBlock ? (
          <View style={[
            styles.dateBlock,
            {
              backgroundColor: 'rgba(245,136,48,0.10)',
              borderColor: 'rgba(245,136,48,0.30)',
            },
          ]}>
            <Text style={[styles.dateMonth, { color: colors.brand }]}>{dateBlock.month}</Text>
            <Text style={[styles.dateDay, { color: colors.brand }]}>{dateBlock.day}</Text>
            <Text style={[styles.dateYear, { color: t.textMuted }]}>{dateBlock.year}</Text>
          </View>
        ) : (
          <View style={[styles.dateBlock, { backgroundColor: 'transparent', borderColor: t.border }]}>
            <Text style={[styles.dateMonth, { color: t.textMuted }]}>—</Text>
          </View>
        )}
      </View>
    </NeuCard>
  );
}

/** Parsea "YYYY-MM-DD" a { day: 15, month: 'MAR', year: 2026 } */
function parseDateBlock(iso: string | null): { day: number; month: string; year: number } | null {
  if (!iso) return null;
  try {
    const d = new Date(`${iso}T00:00:00`);
    const months = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC'];
    return {
      day:   d.getDate(),
      month: months[d.getMonth()],
      year:  d.getFullYear(),
    };
  } catch {
    return null;
  }
}

const styles = StyleSheet.create({
  safe:    { flex: 1 },
  evalBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 5,
    paddingHorizontal: spacing.md, paddingVertical: 8,
    borderRadius: radius.full, backgroundColor: 'rgba(245,136,48,0.12)',
  },
  evalBtnText: { color: colors.brand, fontSize: typography.xs, fontWeight: typography.black },
  searchWrap: {
    flexDirection: 'row', alignItems: 'center',
    marginHorizontal: spacing.xl, marginBottom: spacing.sm,
    borderWidth: 1,
    borderRadius: radius.md,
  },
  search: {
    flex: 1,
    padding: spacing.md,
    fontSize: typography.base,
  },

  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  empty:   { alignItems: 'center', padding: spacing.huge },
  emptyText: { fontSize: typography.sm },

  card: { overflow: 'hidden' },
  preview: {
    height: 90,
    overflow: 'hidden',
    justifyContent: 'space-between',
    padding: spacing.md,
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  previewDecor: {
    position: 'absolute',
    right: -14, bottom: -22,
    transform: [{ rotate: '-12deg' }],
  },
  previewBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 5,
    paddingHorizontal: spacing.sm, paddingVertical: 3,
    borderRadius: radius.full,
    backgroundColor: 'rgba(0,0,0,0.30)',
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.30)',
    alignSelf: 'flex-start',
  },
  previewBadgeText: {
    color: '#FFFFFF',
    fontSize: typography.xs - 2, fontWeight: typography.black,
    letterSpacing: 1.5,
  },
  previewSeal: {
    minWidth: 56,
    paddingVertical: spacing.xs, paddingHorizontal: spacing.sm,
    borderRadius: radius.md,
    backgroundColor: 'rgba(255,255,255,0.18)',
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.30)',
    alignItems: 'center', justifyContent: 'center',
  },
  previewSealNum: {
    color: '#FFFFFF',
    fontSize: typography.lg, fontWeight: typography.black,
    letterSpacing: -0.5, lineHeight: typography.lg,
  },
  previewSealLabel: {
    color: 'rgba(255,255,255,0.85)',
    fontSize: typography.xs - 2, fontWeight: typography.black,
    letterSpacing: 1, marginTop: 1,
  },

  body: {
    flexDirection: 'row',
    gap: spacing.md,
    padding: spacing.base,
    alignItems: 'center',
  },
  cardTitle: {
    fontSize: typography.base, fontWeight: typography.black,
    letterSpacing: -0.2,
  },
  cardLote: { fontSize: typography.xs, marginTop: 2, opacity: 0.8 },
  cardFooter: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    marginTop: spacing.xs,
  },
  cardCta: {
    fontSize: typography.xs,
    fontWeight: typography.black,
    letterSpacing: 0.4,
    textTransform: 'uppercase',
  },

  dateBlock: {
    minWidth: 64,
    alignItems: 'center', justifyContent: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: 6,
    borderRadius: radius.md,
    borderWidth: 1,
  },
  dateMonth: {
    fontSize: typography.xs, fontWeight: typography.black,
    letterSpacing: 1, lineHeight: typography.xs + 2,
  },
  dateDay: {
    fontSize: typography.xxl, fontWeight: typography.black,
    letterSpacing: -1, lineHeight: typography.xxl,
    marginVertical: 2,
  },
  dateYear: {
    fontSize: typography.xs - 1, fontWeight: typography.bold,
    letterSpacing: 0.4,
  },
});
