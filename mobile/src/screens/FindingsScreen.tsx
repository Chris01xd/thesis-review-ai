import React from "react";
import { ScrollView, Text, View, StyleSheet } from "react-native";
import { findings } from "../data/mockData";
import { colors, severityColor } from "../theme/theme";

export function FindingsScreen() {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Hallazgos IA</Text>
      <Text style={styles.subtitle}>Organizados por severidad. Vista solo lectura para estudiantes.</Text>
      {findings.map((f) => (
        <View key={f.id} style={styles.card}>
          <View style={styles.header}>
            <Text style={[styles.badge, { backgroundColor: severityColor(f.severity) }]}>{f.severity}</Text>
            <Text style={styles.section}>{f.section}</Text>
          </View>
          <Text style={styles.label}>Descripción</Text>
          <Text style={styles.text}>{f.description}</Text>
          <Text style={styles.label}>Cómo corregir</Text>
          <Text style={styles.text}>{f.correction}</Text>
          <Text style={styles.label}>Ejemplo</Text>
          <Text style={styles.example}>{f.example}</Text>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: colors.background },
  content: { padding: 18 },
  title: { fontSize: 26, fontWeight: "800", color: colors.text },
  subtitle: { color: colors.muted, marginTop: 4, marginBottom: 12 },
  card: {
    backgroundColor: colors.card,
    borderRadius: 18,
    padding: 16,
    borderColor: colors.border,
    borderWidth: 1,
    marginBottom: 12
  },
  header: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 },
  badge: { color: "white", paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, fontWeight: "700", overflow: "hidden" },
  section: { fontWeight: "700", color: colors.text, flex: 1 },
  label: { marginTop: 10, color: colors.secondary, fontWeight: "800" },
  text: { color: colors.text, lineHeight: 20, marginTop: 3 },
  example: { color: colors.muted, lineHeight: 20, marginTop: 3, fontStyle: "italic" }
});
