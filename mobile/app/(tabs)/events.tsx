import { useEffect, useState, useCallback } from 'react';
import {
  Dimensions, FlatList, Image, Pressable, RefreshControl,
  StyleSheet, Text, View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';

import { api } from '@/api/client';
import {
  brandScale, colors, radius, spacing, TAB_BAR_HEIGHT, themed, typography,
} from '@/theme/tokens';
import { useTheme } from '@/stores/theme';
import { Loader, ScreenHeader, VBackground } from '@/components/ui';

const { width: SCREEN_W } = Dimensions.get('window');
const GRID_GAP = 10;
const GRID_PADDING = 14;
const CARD_W = (SCREEN_W - GRID_PADDING * 2 - GRID_GAP) / 2;

type Status = 'asisti' | 'inscrito' | 'no_asisti' | 'disponible';
type Event = {
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
  location: string;
  meeting_url: string;
  banner_url: string | null;
  is_active: boolean;
  status: Status;
  has_resumen?: boolean;
};
type EventosResponse = {
  tab: 'mios' | 'disponibles';
  count_mios: number;
  count_disponibles: number;
  results: Event[];
};

const STATUS_TONE: Record<Status, 'success' | 'brand' | 'danger' | 'info'> = {
  asisti: 'success', inscrito: 'brand', no_asisti: 'danger', disponible: 'info',
};
const STATUS_LABEL: Record<Status, string> = {
  asisti: 'Asistí', inscrito: 'Inscrito', no_asisti: 'No asistí', disponible: 'Disponible',
};

export default function EventosScreen() {
  const [tab, setTab] = useState<'mios' | 'disponibles'>('mios');
  const [data, setData] = useState<EventosResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const theme = useTheme();
  const t = themed(theme);

  const load = useCallback(async () => {
    try {
      const res = await api.get<EventosResponse>(
        `/api/v1/public/account/events/?tab=${tab}`
      );
      setData(res);
    } catch {
      // silencio
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [tab]);

  useEffect(() => { setLoading(true); load(); }, [load]);

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: t.bg }]}>
      <VBackground intensity={theme === 'dark' ? 0.55 : 0.3} variant="mixed" />
      <ScreenHeader
        eyebrow="EVENTOS"
        title={tab === 'mios' ? 'Mis eventos' : 'Disponibles'}
        gradientTitle
      />

      <View style={styles.tabs}>
        <TabBtn
          label={`Mis eventos${data ? ` (${data.count_mios})` : ''}`}
          active={tab === 'mios'}
          onPress={() => setTab('mios')}
          theme={theme}
        />
        <TabBtn
          label={`Disponibles${data ? ` (${data.count_disponibles})` : ''}`}
          active={tab === 'disponibles'}
          onPress={() => setTab('disponibles')}
          theme={theme}
        />
      </View>

      {loading ? (
        <View style={styles.loading}><Loader size={88} /></View>
      ) : (
        <FlatList
          contentContainerStyle={{
            paddingHorizontal: GRID_PADDING,
            paddingTop: spacing.sm,
            paddingBottom: TAB_BAR_HEIGHT + spacing.lg,
          }}
          columnWrapperStyle={{ gap: GRID_GAP, marginBottom: GRID_GAP }}
          numColumns={2}
          data={data?.results ?? []}
          keyExtractor={(e) => String(e.id)}
          renderItem={({ item }) => <EventoCard evento={item} />}
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
                {tab === 'mios'
                  ? 'Aún no estás inscrito en ningún evento.'
                  : 'No hay eventos disponibles por ahora.'}
              </Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}

function TabBtn({
  label, active, onPress, theme,
}: { label: string; active: boolean; onPress: () => void; theme: 'light' | 'dark' }) {
  const t = themed(theme);
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.tabBtn,
        {
          backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(15,23,42,0.04)',
          borderColor: t.border,
        },
        active && { backgroundColor: colors.brand, borderColor: colors.brand },
        pressed && { opacity: 0.85 },
      ]}
    >
      <Text style={[
        styles.tabBtnText,
        { color: t.textMuted },
        active && { color: '#FFFFFF', fontWeight: typography.black },
      ]}>
        {label}
      </Text>
    </Pressable>
  );
}

function EventoCard({ evento }: { evento: Event }) {
  const theme = useTheme();
  const t = themed(theme);

  // Si hay resumen IA listo y soy parte del evento (inscrito/asistí/no asistí),
  // la card abre directo al resumen. Sino, abre el detalle normal.
  const verResumenDirecto =
    evento.has_resumen && evento.status !== 'disponible';

  function onTap() {
    if (verResumenDirecto) {
      router.push({ pathname: '/event/resumen/[id]', params: { id: String(evento.id) } });
    } else {
      router.push({ pathname: '/event/[id]', params: { id: String(evento.id) } });
    }
  }

  // Hero gradient según modalidad (mismo estilo del web)
  const heroColors: [string, string, string] = evento.es_virtual
    ? ['#1E3A8A', '#1E40AF', '#0F1F4D']
    : [brandScale[500], '#E8721C', brandScale[700]];

  const dateBlock = formatDateBlock(evento.date);
  const dayLabel = (evento.day_of_week || '').slice(0, 3).toUpperCase();
  const time = evento.start_time.slice(0, 5);

  return (
    <Pressable
      onPress={onTap}
      style={({ pressed }) => [
        styles.card,
        { backgroundColor: t.cardSoft, borderColor: t.border },
        pressed && { transform: [{ scale: 0.97 }], opacity: 0.92 },
      ]}
    >
      {/* HERO con banner o gradient */}
      <View style={styles.cardHero}>
        {evento.banner_url ? (
          <Image source={{ uri: evento.banner_url }} style={styles.cardBanner} resizeMode="cover" />
        ) : (
          <LinearGradient
            colors={heroColors}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={StyleSheet.absoluteFill}
          />
        )}
        {/* Overlay para legibilidad de pills */}
        <View style={styles.cardOverlay} />

        {/* Pill modalidad */}
        <View style={styles.cardModPill}>
          <Ionicons
            name={evento.es_virtual ? 'videocam' : 'business'}
            size={9}
            color="#FFFFFF"
          />
          <Text style={styles.cardModText}>
            {evento.es_virtual ? 'Virtual' : 'Presencial'}
          </Text>
        </View>

        {/* Pill estado (si no es 'disponible') */}
        {evento.status !== 'disponible' ? (
          <View style={[
            styles.cardStatusPill,
            { backgroundColor: STATUS_BG[evento.status], borderColor: STATUS_BORDER[evento.status] },
          ]}>
            <Ionicons name={STATUS_ICON[evento.status]} size={9} color={STATUS_FG[evento.status]} />
            <Text style={[styles.cardStatusText, { color: STATUS_FG[evento.status] }]}>
              {STATUS_LABEL[evento.status]}
            </Text>
          </View>
        ) : null}

        {/* Día block grande estilo iPhone */}
        <View style={styles.cardDateBlock}>
          <Text style={styles.cardDateDay}>{dateBlock.day}</Text>
          <Text style={styles.cardDateMonth}>{dateBlock.month}</Text>
        </View>
      </View>

      {/* Cuerpo */}
      <View style={styles.cardBody}>
        <Text style={[styles.cardTitle, { color: t.text }]} numberOfLines={2}>
          {evento.titulo_display}
        </Text>
        <View style={styles.cardMetaRow}>
          <Ionicons name="time" size={11} color={colors.brand} />
          <Text style={[styles.cardMeta, { color: t.textMuted }]} numberOfLines={1}>
            {dayLabel} · {time}
          </Text>
        </View>
        {evento.location && !evento.es_virtual && !verResumenDirecto ? (
          <View style={styles.cardMetaRow}>
            <Ionicons name="location" size={11} color={colors.brand} />
            <Text style={[styles.cardMeta, { color: t.textMuted }]} numberOfLines={1}>{evento.location}</Text>
          </View>
        ) : null}

        {/* Footer CTA al resumen IA — reemplaza meta cuando hay resumen listo */}
        {verResumenDirecto ? (
          <View style={styles.cardBettoFooter}>
            <View style={styles.cardBettoBadge}>
              <Ionicons name="sparkles" size={9} color="#FFFFFF" />
            </View>
            <Text style={styles.cardBettoText} numberOfLines={1}>
              Ver con Betto
            </Text>
            <Ionicons name="arrow-forward" size={11} color={colors.brand} />
          </View>
        ) : null}
      </View>
    </Pressable>
  );
}

const STATUS_BG: Record<Status, string> = {
  asisti: 'rgba(16,185,129,0.95)',
  inscrito: 'rgba(245,136,48,0.95)',
  no_asisti: 'rgba(239,68,68,0.95)',
  disponible: 'rgba(255,255,255,0.92)',
};
const STATUS_BORDER: Record<Status, string> = {
  asisti: 'rgba(255,255,255,0.40)',
  inscrito: 'rgba(255,255,255,0.40)',
  no_asisti: 'rgba(255,255,255,0.40)',
  disponible: 'rgba(15,23,42,0.10)',
};
const STATUS_FG: Record<Status, string> = {
  asisti: '#FFFFFF',
  inscrito: '#FFFFFF',
  no_asisti: '#FFFFFF',
  disponible: '#0F172A',
};
const STATUS_ICON: Record<Status, React.ComponentProps<typeof Ionicons>['name']> = {
  asisti: 'checkmark-circle',
  inscrito: 'bookmark',
  no_asisti: 'close-circle',
  disponible: 'compass',
};

/** "2026-05-03" → { day: '03', month: 'MAY' } */
function formatDateBlock(iso: string): { day: string; month: string } {
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

const styles = StyleSheet.create({
  safe: { flex: 1 },

  tabs: {
    flexDirection: 'row', gap: spacing.sm,
    paddingHorizontal: spacing.base, marginBottom: spacing.sm,
  },
  tabBtn: {
    flex: 1,
    borderWidth: 1,
    borderRadius: radius.md,
    paddingVertical: spacing.sm, alignItems: 'center',
  },
  tabBtnText: {
    fontSize: typography.sm, fontWeight: typography.bold,
  },

  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  empty:   { alignItems: 'center', padding: spacing.huge },
  emptyText: { fontSize: typography.sm, textAlign: 'center' },

  // Card grid 2-col
  card: {
    width: CARD_W,
    borderRadius: radius.xl,
    borderWidth: 1,
    overflow: 'hidden',
    shadowColor: '#0F172A',
    shadowOpacity: 0.10,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 4,
  },
  cardHero: {
    height: 110,
    width: '100%',
    position: 'relative',
    overflow: 'hidden',
  },
  cardBanner: { ...StyleSheet.absoluteFillObject, width: '100%', height: '100%' },
  cardOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.18)',
  },
  cardModPill: {
    position: 'absolute',
    top: 8, left: 8,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.full,
    backgroundColor: 'rgba(0,0,0,0.45)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.30)',
  },
  cardModText: {
    color: '#FFFFFF',
    fontSize: 9,
    fontWeight: typography.black,
    letterSpacing: 0.5,
  },
  cardStatusPill: {
    position: 'absolute',
    top: 8, right: 8,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.full,
    borderWidth: 1,
  },
  cardStatusText: {
    fontSize: 9,
    fontWeight: typography.black,
    letterSpacing: 0.4,
  },
  cardDateBlock: {
    position: 'absolute',
    bottom: 8, left: 8,
    minWidth: 42,
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: radius.md,
    backgroundColor: 'rgba(255,255,255,0.96)',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.20,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 3 },
    elevation: 3,
  },
  cardDateDay: {
    fontSize: 17,
    fontWeight: typography.black,
    color: '#0F172A',
    letterSpacing: -0.5,
    lineHeight: 19,
  },
  cardDateMonth: {
    fontSize: 9,
    fontWeight: typography.black,
    color: colors.brand,
    letterSpacing: 0.8,
    marginTop: -1,
  },
  cardBody: {
    padding: 12,
    gap: 4,
  },
  cardTitle: {
    fontSize: typography.sm + 1,
    fontWeight: typography.black,
    letterSpacing: -0.2,
    lineHeight: (typography.sm + 1) * 1.25,
    minHeight: (typography.sm + 1) * 1.25 * 2,  // reserva 2 líneas para alineación uniforme
  },
  cardMetaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    marginTop: 2,
  },
  cardMeta: {
    fontSize: typography.xs,
    fontWeight: typography.medium,
    flex: 1,
  },

  cardBettoFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 4,
    paddingTop: 6,
    borderTopWidth: 1,
    borderTopColor: 'rgba(245,136,48,0.20)',
  },
  cardBettoBadge: {
    width: 16, height: 16,
    borderRadius: 8,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardBettoText: {
    flex: 1,
    fontSize: typography.xs,
    fontWeight: typography.black,
    color: colors.brand,
    letterSpacing: 0.2,
  },
});
