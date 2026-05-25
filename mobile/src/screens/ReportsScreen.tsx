import React from "react";
import { ScrollView, Text, View, StyleSheet, Alert } from "react-native";
import { Button } from "react-native-paper";
import { colors } from "../theme/theme";

export function ReportsScreen() {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Reportes PDF</Text>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Acta de revisión IA + asesor</Text>
        <Text style={styles.text}>Incluye hallazgos, nota IA, validación humana y recomendaciones.</Text>
        <Button mode="contained" style={styles.button} onPress={() => Alert.alert("Demo", "En producción descarga el PDF desde la API web.")}>
          Descargar reporte
        </Button>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Comparativo de versiones</Text>
        <Text style={styles.text}>Muestra la evolución de nota y cumplimiento entre versiones del avance.</Text>
        <Button mode="outlined" style={styles.button} onPress={() => Alert.alert("Demo", "Reporte disponible cuando la API esté conectada.")}>
          Ver reporte
        </Button>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: colors.background },
  content: { padding: 18 },
  title: { fontSize: 26, fontWeight: "800", color: colors.text, marginBottom: 12 },
  card: { backgroundColor: colors.card, borderRadius: 18, padding: 16, borderColor: colors.border, borderWidth: 1, marginBottom: 12 },
  cardTitle: { fontSize: 17, fontWeight: "800", color: colors.text },
  text: { color: colors.muted, marginTop: 8, lineHeight: 20 },
  button: { marginTop: 14 }
});
