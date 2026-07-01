/**
 * Evaluación formal (programa/seminario) — rendir y enviar.
 *
 * A diferencia del cuestionario de repaso, NO revela la respuesta hasta enviar:
 * el estudiante responde todas y el servidor califica. Muestra nota, si aprobó
 * y una revisión pregunta por pregunta.
 */
import { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import * as Haptics from 'expo-haptics';

import { api, APIError } from '@/api/client';
import { brandScale, colors, radius, shadows, spacing, typography } from '@/theme/tokens';
import { Loader, useToast } from '@/components/ui';

type Question = { id: number; text: string; kind: string; options: string[] };
type EvalPayload = {
  id: number;
  title: string;
  description: string;
  owner_label: string;
  pass_threshold: number;
  attempts_allowed: number;
  attempts_used: number;
  can_attempt: boolean;
  best_score: number | null;
  passed: boolean;
  questions?: Question[];
};
type SubmitResult = {
  score: number; correct: number; total: number; passed: boolean;
  pass_threshold: number; attempts_used: number; attempts_allowed: number;
  detail: { question_id: number; chosen_idx: number; correct_idx: number; is_correct: boolean; explanation: string }[];
};

export default function EvaluationScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const toast = useToast();

  const [data, setData] = useState<EvalPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [idx, setIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<SubmitResult | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get<EvalPayload>(`/api/v1/public/account/evaluations/${id}/`);
        setData(res);
      } catch (e: any) {
        toast.error(e?.message ?? 'No se pudo cargar', 'Error');
      } finally {
        setLoading(false);
      }
    })();
  }, [id, toast]);

  const questions = data?.questions ?? [];
  const total = questions.length;
  const answeredCount = Object.keys(answers).length;

  function choose(qid: number, optIdx: number) {
    setAnswers((prev) => ({ ...prev, [qid]: optIdx }));
    Haptics.selectionAsync().catch(() => {});
  }

  async function submit() {
    setSubmitting(true);
    try {
      const res = await api.post<SubmitResult>(
        `/api/v1/public/account/evaluations/${id}/submit/`,
        { answers },
      );
      setResult(res);
      Haptics.notificationAsync(
        res.passed ? Haptics.NotificationFeedbackType.Success : Haptics.NotificationFeedbackType.Error,
      ).catch(() => {});
    } catch (e: any) {
      const msg = e instanceof APIError ? (e.data?.error ?? e.message) : (e?.message ?? 'Error');
      toast.error(msg, 'No se envió');
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <View style={styles.loading}><Loader size={88} /></View>;

  // Sin intentos o sin preguntas → estado informativo
  if (!data || !data.can_attempt || total === 0) {
    return (
      <View style={[styles.shell, { paddingTop: insets.top }]}>
        <Gradient />
        <View style={styles.centered}>
          <Ionicons name="clipboard-outline" size={64} color="rgba(255,255,255,0.4)" />
          <Text style={styles.bigMsg}>{data?.title ?? 'Evaluación'}</Text>
          <Text style={styles.subMsg}>
            {total === 0
              ? 'Esta evaluación aún no tiene preguntas.'
              : data?.passed
                ? `¡Ya aprobaste con ${data?.best_score}%!`
                : `Usaste tus ${data?.attempts_allowed} intentos${data?.best_score != null ? ` · mejor nota ${data?.best_score}%` : ''}.`}
          </Text>
          <BackBtn />
        </View>
      </View>
    );
  }

  // Resultado
  if (result) {
    return (
      <View style={[styles.shell, { paddingTop: insets.top }]}>
        <Gradient />
        <ScrollView contentContainerStyle={styles.resultBody} showsVerticalScrollIndicator={false}>
          <View style={[styles.resultSeal, { borderColor: result.passed ? '#10B981' : '#EF4444' }]}>
            <Ionicons name={result.passed ? 'trophy' : 'refresh'} size={44} color={result.passed ? '#6EE7B7' : '#FCA5A5'} />
          </View>
          <Text style={styles.resultScore}>{result.score}%</Text>
          <Text style={[styles.resultVerdict, { color: result.passed ? '#6EE7B7' : '#FCA5A5' }]}>
            {result.passed ? '¡Aprobaste!' : 'No alcanzaste la nota'}
          </Text>
          <Text style={styles.subMsg}>
            {result.correct}/{result.total} correctas · mínimo {result.pass_threshold}%
          </Text>
          {!result.passed && result.attempts_used < result.attempts_allowed ? (
            <Text style={styles.subMsg}>Te quedan {result.attempts_allowed - result.attempts_used} intento(s).</Text>
          ) : null}

          {/* Revisión */}
          <View style={styles.review}>
            {questions.map((q, i) => {
              const d = result.detail.find((x) => x.question_id === q.id);
              const ok = d?.is_correct;
              return (
                <View key={q.id} style={[styles.reviewItem, { borderColor: ok ? 'rgba(16,185,129,0.4)' : 'rgba(239,68,68,0.4)' }]}>
                  <Text style={styles.reviewQ}>{i + 1}. {q.text}</Text>
                  {q.options.map((o, oi) => (
                    <Text key={oi} style={[
                      styles.reviewOpt,
                      oi === d?.correct_idx && styles.reviewCorrect,
                      oi === d?.chosen_idx && oi !== d?.correct_idx && styles.reviewWrong,
                    ]}>
                      {oi === d?.correct_idx ? '✓ ' : oi === d?.chosen_idx ? '✗ ' : '  '}{o}
                    </Text>
                  ))}
                  {d?.explanation ? <Text style={styles.reviewExpl}>{d.explanation}</Text> : null}
                </View>
              );
            })}
          </View>
          <BackBtn label="Volver" />
        </ScrollView>
      </View>
    );
  }

  // Rendir: una pregunta a la vez (sin revelar)
  const q = questions[idx];
  const picked = answers[q.id];
  const isLast = idx + 1 >= total;

  return (
    <View style={[styles.shell, { paddingTop: insets.top }]}>
      <Gradient />
      <View style={styles.topbar}>
        <Text style={styles.evalTitle} numberOfLines={1}>{data.title}</Text>
        <View style={styles.counter}><Text style={styles.counterText}>{idx + 1}/{total}</Text></View>
      </View>
      <View style={styles.progressBar}>
        <View style={[styles.progressFill, { width: `${(answeredCount / total) * 100}%` }]} />
      </View>

      <ScrollView contentContainerStyle={styles.body} showsVerticalScrollIndicator={false}>
        <Text style={styles.question}>{q.text}</Text>
        <View style={styles.options}>
          {q.options.map((opt, i) => {
            const sel = picked === i;
            return (
              <Pressable
                key={i}
                onPress={() => choose(q.id, i)}
                style={({ pressed }) => [
                  styles.opt,
                  sel && styles.optSelected,
                  pressed && { transform: [{ scale: 0.98 }] },
                ]}
              >
                <View style={[styles.optRadio, sel && styles.optRadioOn]}>
                  {sel ? <Ionicons name="checkmark" size={14} color="#FFFFFF" /> : null}
                </View>
                <Text style={styles.optText}>{opt}</Text>
              </Pressable>
            );
          })}
        </View>
      </ScrollView>

      {/* Nav inferior */}
      <View style={[styles.footer, { paddingBottom: insets.bottom + spacing.sm }]}>
        {idx > 0 ? (
          <Pressable onPress={() => setIdx(idx - 1)} style={styles.ghostBtn}>
            <Ionicons name="arrow-back" size={16} color="#FFFFFF" />
            <Text style={styles.ghostText}>Anterior</Text>
          </Pressable>
        ) : <View style={{ flex: 1 }} />}

        {!isLast ? (
          <Pressable onPress={() => setIdx(idx + 1)} style={styles.primaryWrap}>
            <LinearGradient colors={[brandScale[500], brandScale[700]]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.primary}>
              <Text style={styles.primaryText}>Siguiente</Text>
              <Ionicons name="arrow-forward" size={16} color="#FFFFFF" />
            </LinearGradient>
          </Pressable>
        ) : (
          <Pressable onPress={submit} disabled={submitting || answeredCount < total} style={[styles.primaryWrap, (submitting || answeredCount < total) && { opacity: 0.5 }]}>
            <LinearGradient colors={['#10B981', '#059669']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.primary}>
              <Text style={styles.primaryText}>{submitting ? 'Enviando…' : answeredCount < total ? `Faltan ${total - answeredCount}` : 'Enviar'}</Text>
              {!submitting ? <Ionicons name="checkmark-done" size={16} color="#FFFFFF" /> : null}
            </LinearGradient>
          </Pressable>
        )}
      </View>
    </View>
  );
}

function Gradient() {
  return <LinearGradient colors={['#0F1A4D', '#162054', '#0F1A4D']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={StyleSheet.absoluteFill} />;
}
function BackBtn({ label = 'Volver' }: { label?: string }) {
  return (
    <Pressable onPress={() => router.back()} style={styles.primaryWrap}>
      <LinearGradient colors={[brandScale[500], brandScale[700]]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.primary}>
        <Ionicons name="arrow-back" size={16} color="#FFFFFF" />
        <Text style={styles.primaryText}>{label}</Text>
      </LinearGradient>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  shell: { flex: 1, backgroundColor: '#0F1A4D' },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#0F1A4D' },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing.base, paddingHorizontal: spacing.xl },
  bigMsg: { color: '#FFFFFF', fontSize: typography.xl, fontWeight: typography.black, textAlign: 'center' },
  subMsg: { color: 'rgba(255,255,255,0.7)', fontSize: typography.sm, textAlign: 'center', fontWeight: typography.medium },

  topbar: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, paddingHorizontal: spacing.base, paddingVertical: spacing.sm },
  evalTitle: { flex: 1, color: '#FFFFFF', fontSize: typography.base, fontWeight: typography.black },
  counter: { paddingHorizontal: spacing.sm, paddingVertical: 5, borderRadius: radius.full, backgroundColor: 'rgba(255,255,255,0.10)' },
  counterText: { color: '#FFFFFF', fontSize: typography.xs, fontWeight: typography.black },
  progressBar: { height: 6, marginHorizontal: spacing.base, borderRadius: 3, backgroundColor: 'rgba(255,255,255,0.10)', overflow: 'hidden' },
  progressFill: { height: '100%', borderRadius: 3, backgroundColor: brandScale[500] },

  body: { padding: spacing.base, gap: spacing.lg, paddingBottom: spacing.xxl },
  question: { color: '#FFFFFF', fontSize: typography.lg, fontWeight: typography.black, lineHeight: typography.lg * 1.3, marginTop: spacing.sm },
  options: { gap: spacing.sm },
  opt: {
    flexDirection: 'row', alignItems: 'center', gap: spacing.sm, padding: spacing.base,
    borderRadius: radius.lg, backgroundColor: 'rgba(255,255,255,0.06)',
    borderWidth: 2, borderColor: 'rgba(255,255,255,0.10)',
  },
  optSelected: { borderColor: colors.brand, backgroundColor: 'rgba(245,136,48,0.15)' },
  optRadio: {
    width: 24, height: 24, borderRadius: 12, borderWidth: 2, borderColor: 'rgba(255,255,255,0.3)',
    alignItems: 'center', justifyContent: 'center',
  },
  optRadioOn: { backgroundColor: colors.brand, borderColor: colors.brand },
  optText: { flex: 1, color: '#FFFFFF', fontSize: typography.sm, fontWeight: typography.bold, lineHeight: typography.sm * 1.35 },

  footer: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, paddingHorizontal: spacing.base, paddingTop: spacing.sm },
  ghostBtn: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs, paddingVertical: 12, paddingHorizontal: spacing.base, borderRadius: radius.lg, backgroundColor: 'rgba(255,255,255,0.10)' },
  ghostText: { color: '#FFFFFF', fontSize: typography.sm, fontWeight: typography.black },
  primaryWrap: { flex: 1, borderRadius: radius.lg, overflow: 'hidden', ...shadows.brand },
  primary: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: spacing.xs, paddingVertical: 14 },
  primaryText: { color: '#FFFFFF', fontSize: typography.sm, fontWeight: typography.black },

  resultBody: { alignItems: 'center', padding: spacing.base, paddingVertical: spacing.xxl, gap: spacing.sm },
  resultSeal: { width: 96, height: 96, borderRadius: 48, borderWidth: 4, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(0,0,0,0.25)' },
  resultScore: { fontSize: 64, fontWeight: typography.black, color: '#FFFFFF', letterSpacing: -2, marginTop: spacing.sm },
  resultVerdict: { fontSize: typography.lg, fontWeight: typography.black },
  review: { width: '100%', gap: spacing.sm, marginTop: spacing.lg },
  reviewItem: { padding: spacing.base, borderRadius: radius.lg, backgroundColor: 'rgba(0,0,0,0.25)', borderWidth: 1, gap: 4 },
  reviewQ: { color: '#FFFFFF', fontSize: typography.sm, fontWeight: typography.black, marginBottom: 4 },
  reviewOpt: { color: 'rgba(255,255,255,0.6)', fontSize: typography.sm - 1, lineHeight: (typography.sm - 1) * 1.5 },
  reviewCorrect: { color: '#6EE7B7', fontWeight: typography.black },
  reviewWrong: { color: '#FCA5A5', fontWeight: typography.bold, textDecorationLine: 'line-through' },
  reviewExpl: { color: 'rgba(255,255,255,0.55)', fontSize: typography.xs, fontStyle: 'italic', marginTop: 4 },
});
