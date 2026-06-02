import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import {
  colors, radius, shadows, spacing, TAB_BAR_HEIGHT, themed, typography,
} from '@/theme/tokens';
import { useAuth } from '@/stores/auth';
import { useTheme, useThemeStore } from '@/stores/theme';
import { Badge, Button, NeuCard, ScreenHeader } from '@/components/ui';

export default function PerfilScreen() {
  const participante = useAuth((s) => s.participante);
  const logout = useAuth((s) => s.logout);
  const theme = useTheme();
  const t = themed(theme);
  const mode = useThemeStore((s) => s.mode);
  const setMode = useThemeStore((s) => s.setMode);

  function confirmarLogout() {
    Alert.alert(
      'Cerrar sesión',
      '¿Seguro que quieres salir?',
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Salir', style: 'destructive', onPress: () => logout() },
      ],
    );
  }

  if (!participante) return null;

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: t.bg }]}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <ScreenHeader eyebrow="MI CUENTA" title="Perfil" />

        {/* Avatar */}
        <View style={styles.avatarBlock}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{participante.initials}</Text>
          </View>
          <Text style={[styles.nombre, { color: t.text }]}>{participante.nombre_completo}</Text>
          <Text style={[styles.email, { color: t.textMuted }]}>{participante.email}</Text>
          {participante.is_leader ? (
            <View style={{ marginTop: spacing.sm }}>
              <Badge tone="brand" variant="soft" size="md" dot>Líder</Badge>
            </View>
          ) : null}
        </View>

        {/* Datos */}
        <View style={styles.section}>
          <NeuCard padded={false}>
            <DataRow icon="card-outline"     label="Cédula"  value={participante.national_id || '—'} themeColor={t.text} mutedColor={t.textMuted} />
            <View style={[styles.divider, { backgroundColor: t.border }]} />
            <DataRow icon="call-outline"     label="Celular" value={participante.phone || '—'} themeColor={t.text} mutedColor={t.textMuted} />
            <View style={[styles.divider, { backgroundColor: t.border }]} />
            <DataRow
              icon="time-outline"
              label="Último ingreso"
              value={participante.last_login
                ? new Date(participante.last_login).toLocaleString('es-EC', {
                    dateStyle: 'short', timeStyle: 'short',
                  })
                : '—'}
              themeColor={t.text}
              mutedColor={t.textMuted}
            />
          </NeuCard>
        </View>

        {/* Apariencia */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: t.textMuted }]}>APARIENCIA</Text>
          <NeuCard padded={false}>
            <View style={styles.themeRow}>
              <ThemeOption label="Sistema" value="system" current={mode} onPress={setMode} icon="phone-portrait-outline" />
              <ThemeOption label="Claro"   value="light"  current={mode} onPress={setMode} icon="sunny-outline" />
              <ThemeOption label="Oscuro"  value="dark"   current={mode} onPress={setMode} icon="moon-outline" />
            </View>
          </NeuCard>
        </View>

        <View style={{ paddingHorizontal: spacing.xl, marginTop: spacing.xl }}>
          <Button
            onPress={confirmarLogout}
            tone="danger"
            variant="soft"
            size="lg"
            fullWidth
            iconLeft={<Ionicons name="log-out-outline" size={18} color={colors.danger} />}
          >
            Cerrar sesión
          </Button>
        </View>

        <Text style={[styles.footer, { color: t.textMuted }]}>certifai · v1.0</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

function DataRow({
  icon, label, value, themeColor, mutedColor,
}: {
  icon: React.ComponentProps<typeof Ionicons>['name'];
  label: string;
  value: string;
  themeColor: string;
  mutedColor: string;
}) {
  return (
    <View style={styles.row}>
      <View style={styles.rowLeft}>
        <View style={[styles.rowIcon, { backgroundColor: 'rgba(245,136,48,0.12)' }]}>
          <Ionicons name={icon} size={16} color={colors.brand} />
        </View>
        <Text style={[styles.rowLabel, { color: mutedColor }]}>{label}</Text>
      </View>
      <Text style={[styles.rowValue, { color: themeColor }]} numberOfLines={1}>{value}</Text>
    </View>
  );
}

function ThemeOption({
  label, value, current, onPress, icon,
}: {
  label: string;
  value: 'light' | 'dark' | 'system';
  current: 'light' | 'dark' | 'system';
  onPress: (m: 'light' | 'dark' | 'system') => void;
  icon: React.ComponentProps<typeof Ionicons>['name'];
}) {
  const active = current === value;
  return (
    <Pressable
      onPress={() => onPress(value)}
      style={({ pressed }) => [
        styles.themeOpt,
        active && styles.themeOptActive,
        pressed && { opacity: 0.85 },
      ]}
    >
      <Ionicons name={icon} size={20} color={active ? '#FFFFFF' : colors.textMutedDark} />
      <Text style={[styles.themeOptLabel, active && { color: '#FFFFFF' }]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  safe:   { flex: 1 },
  scroll: { paddingBottom: TAB_BAR_HEIGHT + spacing.lg },

  avatarBlock: { alignItems: 'center', marginVertical: spacing.xl, paddingHorizontal: spacing.xl },
  avatar: {
    width: 96, height: 96, borderRadius: 48,
    backgroundColor: colors.brand,
    alignItems: 'center', justifyContent: 'center',
    marginBottom: spacing.base,
    ...shadows.brand,
  },
  avatarText: { color: colors.white, fontSize: typography.xxl, fontWeight: typography.black, letterSpacing: -1 },
  nombre:     { fontSize: typography.lg, fontWeight: typography.black, textAlign: 'center' },
  email:      { fontSize: typography.sm, marginTop: 2 },

  section: { marginHorizontal: spacing.xl, marginTop: spacing.lg },
  sectionTitle: {
    fontSize: typography.xs, fontWeight: typography.black, letterSpacing: 2,
    textTransform: 'uppercase', marginBottom: spacing.sm,
  },

  row: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingVertical: spacing.base, paddingHorizontal: spacing.base,
  },
  rowLeft:  { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  rowIcon:  {
    width: 32, height: 32, borderRadius: radius.md,
    alignItems: 'center', justifyContent: 'center',
  },
  rowLabel: { fontSize: typography.sm, fontWeight: typography.bold },
  rowValue: { fontSize: typography.sm, fontWeight: typography.medium, flexShrink: 1, marginLeft: spacing.base, textAlign: 'right' },
  divider:  { height: 1, marginHorizontal: spacing.base },

  themeRow: {
    flexDirection: 'row', padding: spacing.sm, gap: spacing.sm,
  },
  themeOpt: {
    flex: 1,
    alignItems: 'center', justifyContent: 'center', gap: 4,
    paddingVertical: spacing.md,
    borderRadius: radius.md,
    backgroundColor: 'rgba(255,255,255,0.04)',
  },
  themeOptActive: {
    backgroundColor: colors.brand,
    ...shadows.brand,
  },
  themeOptLabel: {
    color: colors.textMutedDark,
    fontSize: typography.xs,
    fontWeight: typography.bold,
    letterSpacing: 0.5,
  },

  footer: {
    fontSize: typography.xs,
    textAlign: 'center', marginTop: spacing.xl, opacity: 0.6,
  },
});
