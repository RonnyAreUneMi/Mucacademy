/**
 * Lista de evaluaciones que el participante puede rendir (programas/seminarios
 * a los que asistió). Cada una lleva a la pantalla de evaluación.
 */
import { useCallback, useState } from 'react';
import { FlatList, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

import { api } from '@/api/client';
import { colors, radius, spacing, themed, typography } from '@/theme/tokens';
import { useTheme } from '@/stores/theme';
import { Loader, ScreenHeader, VBackground, NeuCard } from '@/components/ui';

type EvalItem = {
  id: number;
  title: string;
  owner_label: string;
  kind: 'program' | 'event';
  pass_threshold: number;
  total_questions: number;
  attempts_allowed: number;
  attempts_used: number;
  can_attempt: boolean;
  best_score: number | null;
  passed: boolean;
};

export default function EvaluationsListScreen() {
  const t = themed(useTheme());
  const [items, setItems] = useState<EvalItem[]>([]);
  const [loading, setLoading] = useState(true);

  useFocusEffect(useCallback(() => {
    let alive = true;
    (async () => {
      try {
        const res = await api.get<{ results: EvalItem[] }>('/api/v1/public/account/evaluations/');
        if (alive) setItems(res.results ?? []);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, []));

  if (loading) return <View style={styles.loading}><Loader size={88} /></View>;

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: t.bg }]}>
      <VBackground intensity={0.3} variant="mixed" />
      <ScreenHeader title="Evaluaciones" subtitle="Programas y seminarios por evaluar" canGoBack backLabel="Certificados" />
      <FlatList
        data={items}
        keyExtractor={(e) => String(e.id)}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Ionicons name="clipboard-outline" size={56} color={t.textMuted} />
            <Text style={[styles.emptyText, { color: t.textMuted }]}>No tienes evaluaciones disponibles.</Text>
          </View>
        }
        renderItem={({ item }) => (
          <NeuCard onPress={() => router.push(`/evaluation/${item.id}` as any)} style={styles.card}>
            <View style={styles.cardRow}>
              <View style={[styles.icon, { backgroundColor: 'rgba(245,136,48,0.12)' }]}>
                <Ionicons name={item.kind === 'program' ? 'git-network' : 'clipboard'} size={20} color={colors.brand} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={[styles.title, { color: t.text }]} numberOfLines={1}>{item.title}</Text>
                <Text style={[styles.sub, { color: t.textMuted }]} numberOfLines={1}>{item.owner_label}</Text>
                <View style={styles.metaRow}>
                  <Meta icon="help-circle-outline" text={`${item.total_questions} preg.`} t={t} />
                  <Meta icon="repeat-outline" text={`${item.attempts_used}/${item.attempts_allowed}`} t={t} />
                  <Meta icon="ribbon-outline" text={`mín ${item.pass_threshold}%`} t={t} />
                </View>
              </View>
              {item.passed ? (
                <View style={styles.passBadge}><Ionicons name="checkmark-circle" size={14} color="#10B981" /><Text style={styles.passText}>{item.best_score}%</Text></View>
              ) : !item.can_attempt ? (
                <View style={styles.lockBadge}><Ionicons name="lock-closed" size={12} color={t.textMuted} /></View>
              ) : (
                <Ionicons name="chevron-forward" size={20} color={t.textMuted} />
              )}
            </View>
          </NeuCard>
        )}
      />
    </SafeAreaView>
  );
}

function Meta({ icon, text, t }: { icon: any; text: string; t: any }) {
  return (
    <View style={styles.meta}>
      <Ionicons name={icon} size={12} color={t.textMuted} />
      <Text style={[styles.metaText, { color: t.textMuted }]}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  list: { padding: spacing.base, gap: spacing.sm, paddingBottom: 120 },
  empty: { alignItems: 'center', gap: spacing.base, paddingVertical: spacing.xxl * 2 },
  emptyText: { fontSize: typography.sm, fontWeight: typography.medium },
  card: { padding: spacing.base },
  cardRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  icon: { width: 44, height: 44, borderRadius: radius.md, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: typography.base, fontWeight: typography.black },
  sub: { fontSize: typography.xs, marginTop: 1 },
  metaRow: { flexDirection: 'row', gap: spacing.sm, marginTop: 6 },
  meta: { flexDirection: 'row', alignItems: 'center', gap: 3 },
  metaText: { fontSize: typography.xs - 1, fontWeight: typography.bold },
  passBadge: { flexDirection: 'row', alignItems: 'center', gap: 3, paddingHorizontal: 8, paddingVertical: 4, borderRadius: radius.full, backgroundColor: 'rgba(16,185,129,0.12)' },
  passText: { color: '#10B981', fontSize: typography.xs, fontWeight: typography.black },
  lockBadge: { width: 28, height: 28, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(148,163,184,0.15)' },
});
