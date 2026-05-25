import React from "react";
import { ScrollView, Text, View, StyleSheet } from "react-native";
import { advances } from "../data/mockData";
import { colors } from "../theme/theme";

export function AdvancesScreen() {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Mis revisiones</Text>
      {advances.map((a) => (
        <View key={a.id} style={styles.card}>
          <Text style={styles.cardTitle}>{a.title}</Text>
          <Text style={styles.muted}>Fecha: {a.date}</Text>
          <Text style={styles.status}>{a.status}</Text>
          <View style={styles.row}>
            <Text style={styles.metric}>Nota: {a.grade}/20</Text>
            <Text style={styles.metric}>IA: {a.score}%</Text>
          </View>
          <Text style={styles.pending}>{a.findingsPending} hallazgos pendientes</Text>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: colors.background },
  content: { padding: 18 },
  title: { fontSize: 26, fontWeight: "800", marginBottom: 12, color: colors.text },
  card: {
    backgroundColor: colors.card,
    borderRadius: 18,
    padding: 16,
    borderColor: colors.border,
    borderWidth: 1,
    marginBottom: 12
  },
  cardTitle: { fontSize: 17, fontWeight: "700", color: colors.text },
  muted: { color: colors.muted, marginTop: 5 },
  status: { color: colors.primary, fontWeight: "700", marginTop: 8 },
  row: { flexDirection: "row", gap: 14, marginTop: 8 },
  metric: { fontWeight: "700", color: colors.text },
  pending: { marginTop: 8, color: colors.warning }
});
