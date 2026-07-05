import { useWindowDimensions } from 'react-native';
import RenderHTML from 'react-native-render-html';

import { colors, spacing, themed, typography } from '@/theme/tokens';
import { useTheme } from '@/stores/theme';

/**
 * RichText — renderiza el HTML guardado por el CKEditor (negritas, listas,
 * títulos, enlaces) con estilos coherentes con el tema. Úsalo en cualquier
 * pantalla que muestre una descripción rica.
 */
export function RichText({
  html,
  contentWidth,
}: {
  html: string;
  contentWidth?: number;
}) {
  const { width } = useWindowDimensions();
  const t = themed(useTheme());

  return (
    <RenderHTML
      contentWidth={contentWidth ?? width - spacing.base * 2}
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
        u:      { textDecorationLine: 'underline' },
        h1:     { color: t.text, fontSize: typography.md, fontWeight: typography.black, marginTop: spacing.base, marginBottom: spacing.xs, letterSpacing: -0.2 },
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
