import React from "react";
import { ScrollView, Text, View, StyleSheet, Dimensions } from "react-native";
import { LineChart } from "react-native-chart-kit";
import { gradeHistory } from "../data/mockData";
import { colors } from "../theme/theme";

export function HistoryScreen() {
  const width = Dimensions.get("window").width - 36;
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Historial de notas</Text>
      <View style={styles.card}>
        <LineChart
          data={{
            labels: gradeHistory.map((g) => g.version),
            datasets: [{ data: gradeHistory.map((g) => g.grade) }]
          }}
          width={width - 32}
          height={220}
          yAxisSuffix=""
          yAxisInterval={1}
          chartConfig={{
            backgroundColor: "#ffffff",
            backgroundGradientFrom: "#ffffff",
            backgroundGradientTo: "#ffffff",
            decimalPlaces: 1,
            color: () => colors.primary,
            labelColor: () => colors.muted,
            propsForDots: { r: "5" }
          }}
          bezier
          style={{ borderRadius: 16 }}
        />
      </View>

      {gradeHistory.map((g) => (
        <View key={g.version} style={styles.item}>
          <Text style={styles.version}>{g.version}</Text>
          <Text style={styles.grade}>{g.grade}/20</Text>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: colors.background },
  content: { padding: 18 },
  title: { fontSize: 26, fontWeight: "800", color: colors.text, marginBottom: 12 },
  card: { backgroundColor: colors.card, borderRadius: 18, padding: 16, borderWidth: 1, borderColor: colors.border },
  item: { flexDirection: "row", justifyContent: "space-between", padding: 16, backgroundColor: colors.card, borderRadius: 14, marginTop: 10, borderWidth: 1, borderColor: colors.border },
  version: { fontWeight: "700", color: colors.text },
  grade: { fontWeight: "800", color: colors.primary }
});
