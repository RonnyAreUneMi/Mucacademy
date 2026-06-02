/**
 * Cuestionario IA — pantalla inmersiva tipo Quizizz para mobile.
 *
 * Características:
 *  - Una pregunta a la vez con animaciones de entrada (Reanimated)
 *  - Timer de 30s por pregunta (alerta a los 5s con haptic)
 *  - 4 opciones grandes coloreadas (rojo/azul/amarillo/verde)
 *  - Haptic al responder (success/error)
 *  - Auto-avance tras 2.5s mostrando feedback
 *  - Pantalla final con score, stats y botones reintentar / volver
 *  - Persiste el resultado vía POST al backend
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import {
  Dimensions, Pressable, ScrollView, StyleSheet, Text, View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import * as Haptics from 'expo-haptics';
import Animated, {
  Easing, FadeIn, FadeOut, useAnimatedStyle, useSharedValue,
  withRepeat, withSequence, withTiming, ZoomIn,
} from 'react-native-reanimated';

import { api, APIError } from '@/api/client';
import {
  brandScale, colors, radius, shadows, spacing, typography,
} from '@/theme/tokens';
import { BettoLogo, Loader, useToast } from '@/components/ui';

type Question = {
  question: string;
  options: string[];
  correct_idx: number;
  explanation?: string;
};

type SummaryPayload = {
  status?: string;
  estado?: string;
  quiz?: Question[];
  intentos_disponibles?: number;
  max_intentos?: number;
};

const TIME_PER_Q = 30;
const AUTO_NEXT_MS = 2500;
const OPT_COLORS: [string, string][] = [
  ['#EF4444', '#DC2626'], // rojo
  ['#3B82F6', '#1D4ED8'], // azul
  ['#F59E0B', '#D97706'], // amarillo
  ['#10B981', '#059669'], // verde
];
const { width: SCREEN_W } = Dimensions.get('window');

export default function CuestionarioScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const toast = useToast();

  const [data, setData] = useState<SummaryPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [idx, setIdx] = useState(0);
  const [answers, setAnswers] = useState<(number | null)[]>([]);
  const [timesUsed, setTimesUsed] = useState<number[]>([]);
  const [timeLeft, setTimeLeft] = useState(TIME_PER_Q);
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [intentosRestantes, setIntentosRestantes] = useState<number | null>(null);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const autoNextRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Carga del cuestionario ─────────────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        const res = await api.get<SummaryPayload>(`/api/v1/public/sessions/${id}/resumen/`);
        setData(res);
        if (res.quiz) {
          setAnswers(new Array(res.quiz.length).fill(null));
          setTimesUsed(new Array(res.quiz.length).fill(TIME_PER_Q));
        }
        if (res.intentos_disponibles === 0) {
          toast.info(`Ya completaste tus ${res.max_intentos ?? 2} intentos.`, 'Sin intentos');
          router.replace(`/event/resumen/${id}`);
        }
      } catch (e: any) {
        toast.error(e?.message ?? 'No se pudo cargar', 'Error');
      } finally {
        setLoading(false);
      }
    })();
  }, [id, toast]);

  // ── Timer por pregunta ─────────────────────────────────────────
  const total = data?.quiz?.length ?? 0;

  const clearTimers = useCallback(() => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    if (autoNextRef.current) { clearTimeout(autoNextRef.current); autoNextRef.current = null; }
  }, []);

  useEffect(() => {
    if (loading || done || !data?.quiz || answers[idx] !== null) return;
    setTimeLeft(TIME_PER_Q);
    timerRef.current = setInterval(() => {
      setTimeLeft(prev => {
        const next = prev - 1;
        if (next === 5) Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
        if (next <= 0) {
          if (timerRef.current) clearInterval(timerRef.current);
          pick(null);
          return 0;
        }
        return next;
      });
    }, 1000);
    return () => clearTimers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idx, loading, done, data?.quiz, answers]);

  // ── Responder ──────────────────────────────────────────────────
  function pick(optIdx: number | null) {
    if (answers[idx] !== null) return;
    clearTimers();
    const used = TIME_PER_Q - timeLeft;
    setTimesUsed(prev => {
      const copy = [...prev];
      copy[idx] = used;
      return copy;
    });
    setAnswers(prev => {
      const copy = [...prev];
      copy[idx] = optIdx;
      return copy;
    });

    const correctIdx = data!.quiz![idx].correct_idx;
    const wasCorrect = optIdx === correctIdx;
    Haptics.notificationAsync(
      wasCorrect ? Haptics.NotificationFeedbackType.Success : Haptics.NotificationFeedbackType.Error
    ).catch(() => {});

    autoNextRef.current = setTimeout(() => {
      if (idx + 1 < total) {
        setIdx(idx + 1);
      } else {
        finish();
      }
    }, AUTO_NEXT_MS);
  }

  async function finish() {
    clearTimers();
    setDone(true);
    setSubmitting(true);
    const tiempoTotal = timesUsed.reduce((a, b) => a + b, 0);
    try {
      const res = await api.post<{ ok: boolean; intentos_restantes: number }>(
        `/api/v1/public/sessions/${id}/cuestionario/submit/`,
        { respuestas: answers, tiempo_total_seg: tiempoTotal },
      );
      setIntentosRestantes(res.intentos_restantes);
    } catch (e: any) {
      const msg = e instanceof APIError ? (e.data?.error ?? e.message) : (e?.message ?? 'Error');
      toast.error(msg, 'No se guardó');
    } finally {
      setSubmitting(false);
    }
  }

  function goNext() {
    clearTimers();
    if (idx + 1 < total) setIdx(idx + 1);
    else finish();
  }

  // ── Render ─────────────────────────────────────────────────────
  if (loading) {
    return <View style={styles.loading}><Loader size={88} /></View>;
  }
  if (!data?.quiz || total === 0) {
    return (
      <View style={[styles.shell, { paddingTop: insets.top + spacing.lg }]}>
        <Text style={styles.empty}>No hay cuestionario disponible.</Text>
      </View>
    );
  }

  if (done) {
    return (
      <ResultScreen
        answers={answers}
        preguntas={data.quiz}
        timesUsed={timesUsed}
        intentosRestantes={intentosRestantes}
        submitting={submitting}
        sesionId={String(id)}
        insetTop={insets.top}
      />
    );
  }

  const q = data.quiz[idx];
  const responded = answers[idx] !== null;
  const correctIdx = q.correct_idx;
  const pickedIdx = answers[idx];

  return (
    <View style={[styles.shell, { paddingTop: insets.top }]}>
      <LinearGradient
        colors={['#0F1A4D', '#162054', '#0F1A4D']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={StyleSheet.absoluteFill}
      />

      {/* Top bar */}
      <View style={styles.topbar}>
        <BettoLogo size={42} />
        <View style={{ flex: 1, gap: 6 }}>
          <View style={styles.topbarRow}>
            <View style={{ flexDirection: 'row', gap: 6 }}>
              <View style={styles.counter}>
                <Text style={styles.counterText}>{idx + 1} / {total}</Text>
              </View>
            </View>
            <TimerPill seconds={timeLeft} />
          </View>
          <View style={styles.progressBar}>
            <View style={[styles.progressFill, { width: `${(idx / total) * 100}%` }]} />
          </View>
        </View>
      </View>

      <ScrollView
        contentContainerStyle={styles.body}
        showsVerticalScrollIndicator={false}
      >
        {/* Pregunta */}
        <Animated.View
          key={`q-${idx}`}
          entering={ZoomIn.springify().damping(12)}
          style={styles.questionWrap}
        >
          <Text style={styles.question}>{q.question}</Text>
        </Animated.View>

        {/* Opciones */}
        <View style={styles.options}>
          {q.options.map((opt, i) => (
            <OptionButton
              key={`${idx}-${i}`}
              letter={String.fromCharCode(65 + i)}
              text={opt}
              colors={OPT_COLORS[i % OPT_COLORS.length]}
              delay={i * 80}
              disabled={responded}
              isCorrect={responded && i === correctIdx}
              isWrong={responded && i === pickedIdx && pickedIdx !== correctIdx}
              isFaded={responded && i !== correctIdx && i !== pickedIdx}
              onPress={() => pick(i)}
            />
          ))}
        </View>

        {/* Feedback + botón Siguiente */}
        {responded ? (
          <Animated.View entering={FadeIn.duration(300)} style={styles.feedbackWrap}>
            <View style={[
              styles.feedback,
              { borderColor: pickedIdx === correctIdx ? 'rgba(16,185,129,0.5)' : 'rgba(239,68,68,0.5)' },
            ]}>
              <View style={[
                styles.feedbackIcon,
                { backgroundColor: pickedIdx === correctIdx ? 'rgba(16,185,129,0.20)' : 'rgba(239,68,68,0.20)' },
              ]}>
                <Ionicons
                  name={pickedIdx === correctIdx ? 'bulb' : pickedIdx === null ? 'time' : 'information-circle'}
                  size={18}
                  color={pickedIdx === correctIdx ? '#6EE7B7' : '#FCA5A5'}
                />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.feedbackEyebrow}>
                  {pickedIdx === correctIdx
                    ? '¡Correcto!'
                    : pickedIdx === null ? 'Tiempo agotado' : 'Incorrecto'}
                </Text>
                {q.explanation ? (
                  <Text style={styles.feedbackText}>{q.explanation}</Text>
                ) : null}
              </View>
            </View>

            <Pressable
              onPress={goNext}
              style={({ pressed }) => [
                styles.nextBtn,
                pressed && { opacity: 0.85, transform: [{ scale: 0.98 }] },
              ]}
            >
              <LinearGradient
                colors={[brandScale[500], brandScale[700]]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.nextBtnGrad}
              >
                <Text style={styles.nextBtnText}>
                  {idx + 1 < total ? 'Siguiente' : 'Ver resultado'}
                </Text>
                <Ionicons name="arrow-forward" size={16} color="#FFFFFF" />
              </LinearGradient>
            </Pressable>
          </Animated.View>
        ) : null}
      </ScrollView>
    </View>
  );
}

// ── Subcomponentes ────────────────────────────────────────────────

function TimerPill({ seconds }: { seconds: number }) {
  const scale = useSharedValue(1);
  const isDanger = seconds <= 5;
  const isWarn = seconds <= 10 && seconds > 5;

  useEffect(() => {
    if (isDanger) {
      scale.value = withRepeat(withSequence(
        withTiming(1.10, { duration: 400, easing: Easing.inOut(Easing.ease) }),
        withTiming(1.00, { duration: 400, easing: Easing.inOut(Easing.ease) }),
      ), -1, false);
    } else {
      scale.value = withTiming(1, { duration: 200 });
    }
  }, [isDanger, scale]);

  const animStyle = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));

  const bg = isDanger ? 'rgba(239,68,68,0.30)'
    : isWarn ? 'rgba(245,158,11,0.25)'
    : 'rgba(255,255,255,0.10)';
  const fg = isDanger ? '#FCA5A5' : isWarn ? '#FBBF24' : '#FFFFFF';

  return (
    <Animated.View style={[styles.timerPill, { backgroundColor: bg }, animStyle]}>
      <Ionicons name="time" size={12} color={fg} />
      <Text style={[styles.timerText, { color: fg }]}>{seconds}s</Text>
    </Animated.View>
  );
}

function OptionButton({
  letter, text, colors: gradColors, delay,
  disabled, isCorrect, isWrong, isFaded, onPress,
}: {
  letter: string;
  text: string;
  colors: [string, string];
  delay: number;
  disabled: boolean;
  isCorrect: boolean;
  isWrong: boolean;
  isFaded: boolean;
  onPress: () => void;
}) {
  const shake = useSharedValue(0);

  useEffect(() => {
    if (isWrong) {
      shake.value = withSequence(
        withTiming(-8, { duration: 60 }),
        withTiming(8, { duration: 60 }),
        withTiming(-6, { duration: 60 }),
        withTiming(0, { duration: 60 }),
      );
    }
  }, [isWrong, shake]);

  const animStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: shake.value }],
    opacity: isFaded ? 0.30 : 1,
  }));

  return (
    <Animated.View
      entering={FadeIn.delay(delay).springify().damping(15)}
      style={[animStyle, styles.optWrap]}
    >
      <Pressable
        disabled={disabled}
        onPress={onPress}
        style={({ pressed }) => [pressed && !disabled && { transform: [{ scale: 0.98 }] }]}
      >
        <LinearGradient
          colors={gradColors}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[
            styles.opt,
            isCorrect && { borderWidth: 4, borderColor: '#10B981' },
            isWrong && { borderWidth: 4, borderColor: '#EF4444' },
          ]}
        >
          <View style={styles.optLetter}>
            <Text style={styles.optLetterText}>{letter}</Text>
          </View>
          <Text style={styles.optText} numberOfLines={3}>{text}</Text>
          {isCorrect ? (
            <Ionicons name="checkmark-circle" size={22} color="#FFFFFF" />
          ) : isWrong ? (
            <Ionicons name="close-circle" size={22} color="#FFFFFF" />
          ) : null}
        </LinearGradient>
      </Pressable>
    </Animated.View>
  );
}

// ── Pantalla final ────────────────────────────────────────────────

function ResultScreen({
  answers, preguntas, timesUsed, intentosRestantes, submitting, sesionId, insetTop,
}: {
  answers: (number | null)[];
  preguntas: Question[];
  timesUsed: number[];
  intentosRestantes: number | null;
  submitting: boolean;
  sesionId: string;
  insetTop: number;
}) {
  const correct: number = answers.reduce<number>(
    (acc, a, i) => acc + (a === preguntas[i].correct_idx ? 1 : 0),
    0,
  );
  const total = preguntas.length;
  const pct = Math.round((correct / total) * 100);
  const avgTime = Math.round(timesUsed.reduce<number>((a, b) => a + b, 0) / total);

  let msg = '', emoji = '';
  if (pct === 100)    { msg = '¡Perfecto! Dominas el tema.'; emoji = '🏆'; }
  else if (pct >= 80) { msg = '¡Excelente! Casi perfecto.';   emoji = '🎯'; }
  else if (pct >= 60) { msg = '¡Bien! Sigue practicando.';    emoji = '👏'; }
  else if (pct >= 40) { msg = 'Vas mejorando, repasá.';       emoji = '📚'; }
  else                { msg = 'Volvé a leer y reintentá.';    emoji = '💪'; }

  return (
    <View style={[styles.shell, { paddingTop: insetTop }]}>
      <LinearGradient
        colors={['#0F1A4D', '#162054', '#0F1A4D']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={StyleSheet.absoluteFill}
      />
      <ScrollView contentContainerStyle={styles.resultBody} showsVerticalScrollIndicator={false}>
        <Animated.View entering={ZoomIn.springify().damping(10)} style={styles.resultTrophyWrap}>
          <View style={styles.resultGlow} />
          <BettoLogo size={96} />
        </Animated.View>

        <Animated.Text
          entering={FadeIn.delay(200).duration(500)}
          style={styles.resultScore}
        >
          {correct}/{total}
        </Animated.Text>

        <Animated.Text
          entering={FadeIn.delay(350).duration(500)}
          style={styles.resultMsg}
        >
          {emoji} {msg}
        </Animated.Text>

        <Animated.View entering={FadeIn.delay(500).duration(400)} style={styles.resultStats}>
          <Stat num={`${pct}%`} lbl="Aciertos" />
          <Stat num={`${correct}`} lbl="Correctas" />
          <Stat num={`${total - correct}`} lbl="Fallaste" />
          <Stat num={`${avgTime}s`} lbl="Promedio" />
        </Animated.View>

        <Animated.View entering={FadeIn.delay(700).duration(400)} style={styles.resultFooter}>
          {submitting ? (
            <Text style={styles.resultStatus}>Guardando resultado…</Text>
          ) : intentosRestantes !== null && intentosRestantes > 0 ? (
            <>
              <Text style={styles.resultStatus}>
                Te queda <Text style={{ color: '#FFFFFF', fontWeight: typography.black }}>{intentosRestantes}</Text> intento{intentosRestantes === 1 ? '' : 's'} más.
              </Text>
              <View style={styles.resultActions}>
                <Pressable
                  onPress={() => router.replace(`/event/cuestionario/${sesionId}`)}
                  style={({ pressed }) => [pressed && { opacity: 0.85 }]}
                >
                  <LinearGradient
                    colors={[brandScale[500], brandScale[700]]}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.actionPrimary}
                  >
                    <Ionicons name="refresh" size={16} color="#FFFFFF" />
                    <Text style={styles.actionPrimaryText}>Volver a intentar</Text>
                  </LinearGradient>
                </Pressable>
                <Pressable
                  onPress={() => router.replace(`/event/resumen/${sesionId}`)}
                  style={({ pressed }) => [styles.actionGhost, pressed && { opacity: 0.7 }]}
                >
                  <Ionicons name="book" size={14} color="#FFFFFF" />
                  <Text style={styles.actionGhostText}>Volver al resumen</Text>
                </Pressable>
              </View>
            </>
          ) : (
            <>
              <Text style={styles.resultStatus}>
                <Ionicons name="flag" size={12} color="rgba(255,255,255,0.85)" />{' '}
                Usaste todos tus intentos.
              </Text>
              <View style={styles.resultActions}>
                <Pressable
                  onPress={() => router.replace(`/event/resumen/${sesionId}`)}
                  style={({ pressed }) => [pressed && { opacity: 0.85 }]}
                >
                  <LinearGradient
                    colors={[brandScale[500], brandScale[700]]}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.actionPrimary}
                  >
                    <Ionicons name="arrow-forward" size={16} color="#FFFFFF" />
                    <Text style={styles.actionPrimaryText}>Ver mis resultados</Text>
                  </LinearGradient>
                </Pressable>
              </View>
            </>
          )}
        </Animated.View>
      </ScrollView>
    </View>
  );
}

function Stat({ num, lbl }: { num: string; lbl: string }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statNum}>{num}</Text>
      <Text style={styles.statLbl}>{lbl}</Text>
    </View>
  );
}

// ── Estilos ──────────────────────────────────────────────────────

const styles = StyleSheet.create({
  shell: { flex: 1, backgroundColor: '#0F1A4D' },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#0F1A4D' },
  empty: { color: '#FFFFFF', fontSize: typography.lg, textAlign: 'center', marginTop: spacing.xxl },

  topbar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingHorizontal: spacing.base,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.06)',
  },
  topbarRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  counter: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 5,
    borderRadius: radius.full,
    backgroundColor: 'rgba(255,255,255,0.10)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.20)',
  },
  counterText: {
    color: '#FFFFFF',
    fontSize: typography.xs,
    fontWeight: typography.black,
  },
  timerPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: spacing.sm,
    paddingVertical: 5,
    borderRadius: radius.full,
  },
  timerText: {
    fontSize: typography.xs,
    fontWeight: typography.black,
  },
  progressBar: {
    height: 6,
    borderRadius: 3,
    backgroundColor: 'rgba(255,255,255,0.10)',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 3,
    backgroundColor: brandScale[500],
  },

  body: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: spacing.base,
    paddingVertical: spacing.lg,
    gap: spacing.xl,
  },

  questionWrap: { alignItems: 'center' },
  question: {
    color: '#FFFFFF',
    fontSize: typography.xl,
    fontWeight: typography.black,
    letterSpacing: -0.5,
    textAlign: 'center',
    lineHeight: typography.xl * 1.25,
    paddingHorizontal: spacing.sm,
  },

  options: { gap: spacing.sm },
  optWrap: { width: '100%' },
  opt: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    padding: spacing.base,
    borderRadius: radius.lg,
    minHeight: 72,
    ...shadows.md,
  },
  optLetter: {
    width: 36, height: 36,
    borderRadius: radius.md,
    backgroundColor: 'rgba(255,255,255,0.20)',
    alignItems: 'center', justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.30)',
  },
  optLetterText: {
    color: '#FFFFFF',
    fontSize: typography.base,
    fontWeight: typography.black,
  },
  optText: {
    flex: 1,
    color: '#FFFFFF',
    fontSize: typography.sm,
    fontWeight: typography.bold,
    lineHeight: typography.sm * 1.35,
  },

  feedbackWrap: { gap: spacing.base },
  feedback: {
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.base,
    borderRadius: radius.lg,
    backgroundColor: 'rgba(0,0,0,0.30)',
    borderWidth: 1,
  },
  feedbackIcon: {
    width: 36, height: 36,
    borderRadius: radius.md,
    alignItems: 'center', justifyContent: 'center',
  },
  feedbackEyebrow: {
    color: '#FFFFFF',
    fontSize: typography.xs - 1,
    fontWeight: typography.black,
    letterSpacing: 1.4,
    marginBottom: 4,
  },
  feedbackText: {
    color: 'rgba(255,255,255,0.85)',
    fontSize: typography.sm,
    fontWeight: typography.medium,
    lineHeight: typography.sm * 1.5,
  },
  nextBtn: {
    alignSelf: 'center',
    borderRadius: radius.full,
    overflow: 'hidden',
    ...shadows.brand,
  },
  nextBtnGrad: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    paddingVertical: 12,
    paddingHorizontal: spacing.lg,
  },
  nextBtnText: {
    color: '#FFFFFF',
    fontSize: typography.sm,
    fontWeight: typography.black,
  },

  // Resultado
  resultBody: {
    flexGrow: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.base,
    paddingVertical: spacing.xxl,
    gap: spacing.base,
  },
  resultTrophyWrap: {
    width: 140, height: 140,
    alignItems: 'center', justifyContent: 'center',
  },
  resultGlow: {
    position: 'absolute',
    width: 140, height: 140,
    borderRadius: 70,
    backgroundColor: 'rgba(245,136,48,0.25)',
  },
  resultScore: {
    fontSize: 72,
    fontWeight: typography.black,
    color: '#FFFFFF',
    letterSpacing: -2,
    lineHeight: 76,
    marginTop: spacing.base,
  },
  resultMsg: {
    color: '#FFFFFF',
    fontSize: typography.base,
    fontWeight: typography.black,
    textAlign: 'center',
    paddingHorizontal: spacing.base,
  },
  resultStats: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: spacing.lg,
    marginTop: spacing.base,
  },
  stat: {
    alignItems: 'center', gap: 2,
    minWidth: SCREEN_W * 0.20,
  },
  statNum: {
    color: '#FFFFFF',
    fontSize: typography.xxl,
    fontWeight: typography.black,
    letterSpacing: -0.5,
  },
  statLbl: {
    color: 'rgba(255,255,255,0.65)',
    fontSize: typography.xs - 1,
    fontWeight: typography.black,
    letterSpacing: 1.4,
    textTransform: 'uppercase',
  },
  resultFooter: {
    alignItems: 'center',
    gap: spacing.base,
    marginTop: spacing.lg,
  },
  resultStatus: {
    color: 'rgba(255,255,255,0.75)',
    fontSize: typography.sm,
    fontWeight: typography.medium,
    textAlign: 'center',
  },
  resultActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    justifyContent: 'center',
  },
  actionPrimary: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    paddingVertical: 12,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.lg,
    ...shadows.brand,
  },
  actionPrimaryText: {
    color: '#FFFFFF',
    fontSize: typography.sm,
    fontWeight: typography.black,
  },
  actionGhost: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    paddingVertical: 12,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.lg,
    backgroundColor: 'rgba(255,255,255,0.10)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.20)',
  },
  actionGhostText: {
    color: '#FFFFFF',
    fontSize: typography.sm,
    fontWeight: typography.black,
  },
});
