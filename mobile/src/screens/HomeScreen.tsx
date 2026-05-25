import React from "react";
import { ScrollView, Text, View, StyleSheet } from "react-native";
import { MetricCard } from "../components/MetricCard";
import { advances, notifications, student } from "../data/mockData";
import { colors } from "../theme/theme";

export function HomeScreen() {
  const latest = advances[0];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.hello}>Hola, {student.name.split(" ")[0]} 👋</Text>
      <Text style={styles.subtitle}>{student.program}</Text>

      <View style={styles.row}>
        <MetricCard title="Última nota" value={`${latest.grade}/20`} subtitle={latest.title} />
        <MetricCard title="Cumplimiento" value={`${latest.score}%`} subtitle={latest.status} />
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Título de tesis</Text>
        <Text style={styles.paragraph}>{student.thesisTitle}</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Notificaciones</Text>
        {notifications.map((n, index) => (
          <Text key={index} style={styles.notification}>• {n}</Text>
        ))}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Asesor</Text>
        <Text style={styles.paragraph}>{student.advisor}</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: colors.background },
  content: { padding: 18 },
  hello: { fontSize: 28, fontWeight: "800", color: colors.text },
  subtitle: { color: colors.muted, marginTop: 4, marginBottom: 12 },
  row: { flexDirection: "row" },
  card: {
    backgroundColor: colors.card,
    borderRadius: 18,
    padding: 16,
    borderColor: colors.border,
    borderWidth: 1,
    marginVertical: 8
  },
  cardTitle: { fontSize: 17, fontWeight: "700", color: colors.text, marginBottom: 8 },
  paragraph: { color: colors.text, lineHeight: 21 },
  notification: { color: colors.text, marginVertical: 4 }
});
