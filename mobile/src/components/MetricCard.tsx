import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { colors } from "../theme/theme";

type Props = {
  title: string;
  value: string;
  subtitle?: string;
};

export function MetricCard({ title, value, subtitle }: Props) {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.value}>{value}</Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    backgroundColor: colors.card,
    borderRadius: 18,
    padding: 16,
    borderColor: colors.border,
    borderWidth: 1,
    margin: 6
  },
  title: { color: colors.muted, fontSize: 12 },
  value: { color: colors.text, fontSize: 28, fontWeight: "800", marginTop: 6 },
  subtitle: { color: colors.muted, fontSize: 12, marginTop: 4 }
});
