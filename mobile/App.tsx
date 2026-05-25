import React, { useEffect, useState } from "react";
import {
  SafeAreaView,
  ScrollView,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  TextInput,
  ActivityIndicator
} from "react-native";
import { StatusBar } from "expo-status-bar";

/*
  IMPORTANTE:
  Cambia esta URL por la IP local de tu laptop.
  Ejemplo:
  const DEFAULT_API_URL = "http://192.168.1.35:8000";
  No uses localhost en el celular, porque localhost sería el propio celular.
*/
const DEFAULT_API_URL = "http://192.168.1.35:8000";
const DEFAULT_STUDENT_ID = 4;

const demoStudent = {
  name: "Christian Alfredo Noriega Oliva",
  program: "Ingeniería de Sistemas",
  advisor: "Dr. Santos Fernández, Juan Pedro",
  thesisTitle:
    "Sistema web inteligente de gestión y predicción de desperdicio alimentario para PyMEs gastronómicas - Valle Jequetepeque 2026"
};

const demoAdvances = [
  { id: 1, title: "Proyecto de tesis - Capítulo I", status: "En revisión humana", grade: 17.3, overall_score: 86.4, total_findings: 4 },
  { id: 2, title: "Marco teórico v2", status: "Observado", grade: 15.6, overall_score: 78.2, total_findings: 7 },
  { id: 3, title: "Introducción v1", status: "Aprobado", grade: 18.2, overall_score: 91.0, total_findings: 1 }
];

const demoFindings = [
  {
    severity: "Mayor",
    section_ref: "Referencias bibliográficas",
    description: "Algunas referencias requieren verificación de DOI o ajuste de formato APA 7.",
    correction_steps: "Revisar autor, año, título, revista y DOI de cada referencia.",
    example_improvement: "Apellido, A. A. (2024). Título del artículo. Revista, 12(2), 30-45. https://doi.org/..."
  },
  {
    severity: "Menor",
    section_ref: "Redacción académica",
    description: "Se recomienda mejorar conectores y evitar oraciones demasiado extensas.",
    correction_steps: "Dividir párrafos largos y emplear conectores lógicos variados.",
    example_improvement: "Asimismo, el sistema propuesto fortalece la toma de decisiones mediante indicadores predictivos."
  },
  {
    severity: "Sugerencia",
    section_ref: "Tipo de avance",
    description: "Resultados, discusión y conclusiones son opcionales para proyecto de tesis o Capítulo I.",
    correction_steps: "Evaluar el documento con una plantilla específica de proyecto de tesis.",
    example_improvement: "Para Capítulo I, priorizar problema, antecedentes, marco teórico, hipótesis, objetivos y limitaciones."
  }
];

function Metric({ title, value, subtitle }: { title: string; value: string; subtitle?: string }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricTitle}>{title}</Text>
      <Text style={styles.metricValue}>{value}</Text>
      {subtitle ? <Text style={styles.muted}>{subtitle}</Text> : null}
    </View>
  );
}

async function getJson(url: string) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("HTTP " + response.status);
  }
  return response.json();
}

export default function App() {
  const [tab, setTab] = useState("Inicio");
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(false);

  const [dashboard, setDashboard] = useState<any>(null);
  const [students, setStudents] = useState<any[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState(DEFAULT_STUDENT_ID);
  const [advances, setAdvances] = useState<any[]>(demoAdvances);
  const [findings, setFindings] = useState<any[]>(demoFindings);
  const [history, setHistory] = useState<any[]>([]);

  const student = dashboard?.student || demoStudent;
  const latest = dashboard?.latest || advances[0];

  const loadData = async (studentIdParam?: number) => {
    const activeStudentId = studentIdParam || selectedStudentId;
    setLoading(true);
    try {
      const allStudents = await getJson(`${apiUrl}/api/students`);
      setStudents(allStudents);

      const exists = allStudents.some((s: any) => Number(s.id) === Number(activeStudentId));
      const finalStudentId = exists ? activeStudentId : (allStudents?.[0]?.id || activeStudentId);

      if (Number(finalStudentId) !== Number(selectedStudentId)) {
        setSelectedStudentId(Number(finalStudentId));
      }

      const dash = await getJson(`${apiUrl}/api/student/${finalStudentId}/dashboard`);
      const adv = await getJson(`${apiUrl}/api/student/${finalStudentId}/advances`);
      const hist = await getJson(`${apiUrl}/api/student/${finalStudentId}/grade-history`);

      setDashboard(dash);
      setAdvances(adv.length ? adv : []);
      setHistory(hist);

      const firstAdvanceId = adv?.[0]?.id;
      if (firstAdvanceId) {
        const f = await getJson(`${apiUrl}/api/advance/${firstAdvanceId}/findings`);
        setFindings(f.length ? f : []);
      } else {
        setFindings([]);
      }

      setConnected(true);
    } catch (e: any) {
      setConnected(false);
      Alert.alert(
        "Modo demo",
        "No se pudo conectar con la API web. La app mostrará datos demo. Verifica la IP y que api_server.py esté ejecutándose."
      );
      setAdvances(demoAdvances);
      setFindings(demoFindings);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(selectedStudentId);
  }, []);

  function Home() {
    return (
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Hola, {(student.name || "Estudiante").split(" ")[0]} 👋</Text>
        <Text style={styles.subtitle}>{student.program || "Programa no registrado"}</Text>

        <View style={styles.connection}>
          <Text style={connected ? styles.connected : styles.disconnected}>
            {connected ? "Conectado a base de datos real" : "Modo demo local"}
          </Text>
        </View>

        {connected && students.length > 0 ? (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Alumno activo</Text>
            <Text style={styles.text}>
              {students.find((s: any) => Number(s.id) === Number(selectedStudentId))?.name || "Selecciona alumno"}
            </Text>
            <View style={styles.studentButtons}>
              {students.map((s: any) => (
                <TouchableOpacity
                  key={s.id}
                  style={[styles.studentButton, Number(s.id) === Number(selectedStudentId) && styles.studentButtonActive]}
                  onPress={() => {
                    setSelectedStudentId(Number(s.id));
                    loadData(Number(s.id));
                  }}
                >
                  <Text style={[styles.studentButtonText, Number(s.id) === Number(selectedStudentId) && styles.studentButtonTextActive]}>
                    {s.name.split(" ")[0]}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        ) : null}

        <View style={styles.row}>
          <Metric
            title="Última nota"
            value={latest?.grade ? `${Number(latest.grade).toFixed(1)}/20` : "--/20"}
            subtitle={latest?.title || "Sin avance"}
          />
          <Metric
            title="Cumplimiento"
            value={latest?.overall_score ? `${Number(latest.overall_score).toFixed(1)}%` : "--%"}
            subtitle="IA académica"
          />
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Título / último avance</Text>
          <Text style={styles.text}>{latest?.title || demoStudent.thesisTitle}</Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Notificaciones</Text>
          <Text style={styles.text}>• Tu revisión IA está lista.</Text>
          <Text style={styles.text}>• El asesor dejó comentarios en tu avance.</Text>
          <Text style={styles.text}>• Revisa tus hallazgos pendientes.</Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Asesor</Text>
          <Text style={styles.text}>{student.advisor || "Sin asesor asignado"}</Text>
        </View>
      </ScrollView>
    );
  }

  function Advances() {
    return (
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Mis avances</Text>
        {advances.length === 0 ? (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Sin avances</Text>
            <Text style={styles.text}>Este alumno todavía no tiene avances cargados o analizados en la plataforma web.</Text>
          </View>
        ) : null}
        {advances.map((a) => (
          <View key={a.id} style={styles.card}>
            <Text style={styles.cardTitle}>{a.title}</Text>
            <Text style={styles.badge}>{a.status}</Text>
            <Text style={styles.text}>Nota: {a.grade ? Number(a.grade).toFixed(1) : "--"}/20</Text>
            <Text style={styles.text}>
              Cumplimiento IA: {a.overall_score ? Number(a.overall_score).toFixed(1) : "--"}%
            </Text>
            <Text style={styles.warning}>{a.total_findings || a.findings_pending || 0} hallazgos registrados</Text>
          </View>
        ))}
      </ScrollView>
    );
  }

  function Findings() {
    return (
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Hallazgos IA</Text>
        <Text style={styles.subtitle}>Vista de solo lectura para estudiantes</Text>
        {findings.length === 0 ? (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Sin hallazgos</Text>
            <Text style={styles.text}>Este alumno no tiene hallazgos IA registrados para su último avance.</Text>
          </View>
        ) : null}
        {findings.map((f, index) => (
          <View key={f.id || index} style={styles.card}>
            <Text style={styles.severity}>{f.severity} · {f.section_ref}</Text>
            <Text style={styles.label}>Descripción</Text>
            <Text style={styles.text}>{f.description}</Text>
            <Text style={styles.label}>Corrección</Text>
            <Text style={styles.text}>{f.correction_steps}</Text>
            <Text style={styles.label}>Ejemplo</Text>
            <Text style={styles.example}>{f.example_improvement}</Text>
          </View>
        ))}
      </ScrollView>
    );
  }

  function Grades() {
    const rows = history.length ? history : advances.map((a, index) => ({ version: index + 1, grade: a.grade, title: a.title }));
    return (
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Historial de notas</Text>
        <View style={styles.card}>
          {rows.map((h, index) => (
            <View key={h.id || index} style={styles.gradeRow}>
              <Text style={styles.cardTitle}>v{h.version || index + 1}</Text>
              <Text style={styles.grade}>{h.grade ? Number(h.grade).toFixed(1) : "--"}/20</Text>
            </View>
          ))}
        </View>
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Evolución</Text>
          <Text style={styles.text}>La tendencia se actualiza según los avances analizados en la plataforma web.</Text>
        </View>
      </ScrollView>
    );
  }

  function Reports() {
    return (
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Reportes</Text>
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Acta de revisión</Text>
          <Text style={styles.text}>Incluye hallazgos IA, validación humana, nota final y recomendaciones.</Text>
          <TouchableOpacity
            style={styles.button}
            onPress={() => Alert.alert("Reporte", "La descarga PDF se genera desde la plataforma web.")}
          >
            <Text style={styles.buttonText}>Ver reporte</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    );
  }

  function Settings() {
    return (
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Conexión API</Text>
        <Text style={styles.subtitle}>Coloca la IP local de tu laptop donde corre FastAPI.</Text>
        <View style={styles.card}>
          <Text style={styles.label}>URL API</Text>
          <TextInput value={apiUrl} onChangeText={setApiUrl} style={styles.input} autoCapitalize="none" />
          <TouchableOpacity style={styles.button} onPress={loadData}>
            <Text style={styles.buttonText}>{loading ? "Conectando..." : "Conectar / Actualizar"}</Text>
          </TouchableOpacity>
          {loading ? <ActivityIndicator style={{ marginTop: 12 }} /> : null}
          <Text style={connected ? styles.connected : styles.disconnected}>
            {connected ? "Conectado correctamente" : "No conectado / modo demo"}
          </Text>
          <Text style={styles.example}>
            Ejemplo: http://192.168.1.35:8000
          </Text>
        </View>

        {connected && students.length > 0 ? (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Seleccionar alumno</Text>
            {students.map((s: any) => (
              <TouchableOpacity
                key={s.id}
                style={[styles.studentRow, Number(s.id) === Number(selectedStudentId) && styles.studentRowActive]}
                onPress={() => {
                  setSelectedStudentId(Number(s.id));
                  loadData(Number(s.id));
                }}
              >
                <Text style={styles.text}>ID {s.id} · {s.name}</Text>
                <Text style={styles.muted}>{s.program || "Sin programa"} · {s.advisor || "Sin asesor"}</Text>
              </TouchableOpacity>
            ))}
          </View>
        ) : null}
      </ScrollView>
    );
  }

  const render = () => {
    if (tab === "Inicio") return <Home />;
    if (tab === "Avances") return <Advances />;
    if (tab === "Hallazgos") return <Findings />;
    if (tab === "Notas") return <Grades />;
    if (tab === "Reportes") return <Reports />;
    return <Settings />;
  };

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="dark" />
      <View style={styles.header}>
        <Text style={styles.headerTitle}>ThesisReview Student</Text>
        <Text style={styles.headerSub}>App móvil de solo lectura</Text>
      </View>

      <View style={styles.body}>{render()}</View>

      <View style={styles.nav}>
        {["Inicio", "Avances", "Hallazgos", "Notas", "Reportes", "API"].map((item) => (
          <TouchableOpacity key={item} onPress={() => setTab(item)} style={[styles.navItem, tab === item && styles.navItemActive]}>
            <Text style={[styles.navText, tab === item && styles.navTextActive]}>{item}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#f8fafc" },
  header: { paddingTop: 14, paddingHorizontal: 18, paddingBottom: 12, backgroundColor: "#ffffff", borderBottomWidth: 1, borderBottomColor: "#e5e7eb" },
  headerTitle: { fontSize: 22, fontWeight: "800", color: "#0f172a" },
  headerSub: { color: "#64748b", marginTop: 2 },
  body: { flex: 1, paddingBottom: 4 },
  content: { padding: 18, paddingBottom: 80 },
  title: { fontSize: 28, fontWeight: "800", color: "#111827" },
  subtitle: { color: "#64748b", marginTop: 4, marginBottom: 12 },
  row: { flexDirection: "row" },
  metric: { flex: 1, backgroundColor: "#ffffff", borderRadius: 18, padding: 16, borderWidth: 1, borderColor: "#e5e7eb", marginRight: 8, marginVertical: 8 },
  metricTitle: { color: "#64748b", fontSize: 12 },
  metricValue: { color: "#111827", fontSize: 25, fontWeight: "800", marginTop: 6 },
  muted: { color: "#64748b", marginTop: 4 },
  card: { backgroundColor: "#ffffff", borderRadius: 18, padding: 16, borderWidth: 1, borderColor: "#e5e7eb", marginVertical: 8 },
  cardTitle: { fontSize: 17, fontWeight: "800", color: "#111827", marginBottom: 6 },
  text: { color: "#111827", lineHeight: 21, marginTop: 4 },
  badge: { color: "#2563eb", fontWeight: "800", marginVertical: 6 },
  warning: { color: "#d97706", fontWeight: "700", marginTop: 6 },
  severity: { color: "#ea580c", fontWeight: "800", marginBottom: 8 },
  label: { color: "#0f172a", fontWeight: "800", marginTop: 10 },
  example: { color: "#64748b", fontStyle: "italic", lineHeight: 20, marginTop: 8 },
  gradeRow: { flexDirection: "row", justifyContent: "space-between", borderBottomWidth: 1, borderBottomColor: "#e5e7eb", paddingVertical: 10 },
  grade: { fontWeight: "800", color: "#2563eb" },
  button: { marginTop: 14, backgroundColor: "#2563eb", padding: 13, borderRadius: 12, alignItems: "center" },
  buttonText: { color: "#ffffff", fontWeight: "800" },
  input: { borderWidth: 1, borderColor: "#cbd5e1", borderRadius: 12, padding: 12, marginTop: 8, color: "#111827" },
  connection: { marginTop: 10, marginBottom: 4 },
  connected: { color: "#16a34a", fontWeight: "800", marginTop: 10 },
  disconnected: { color: "#dc2626", fontWeight: "800", marginTop: 10 },
  nav: {
    flexDirection: "row",
    backgroundColor: "#ffffff",
    borderTopWidth: 1,
    borderTopColor: "#e5e7eb",
    paddingTop: 8,
    paddingBottom: 32,
    paddingHorizontal: 4,
    minHeight: 88
  },
  navItem: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 10,
    borderRadius: 12,
    minHeight: 44
  },
  navItemActive: { backgroundColor: "#eff6ff" },
  navText: { color: "#64748b", fontSize: 9, fontWeight: "700" },
  navTextActive: { color: "#2563eb" },
  studentButtons: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 12 },
  studentButton: { paddingVertical: 8, paddingHorizontal: 12, backgroundColor: "#f1f5f9", borderRadius: 12 },
  studentButtonActive: { backgroundColor: "#2563eb" },
  studentButtonText: { color: "#334155", fontWeight: "800" },
  studentButtonTextActive: { color: "#ffffff" },
  studentRow: { paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: "#e5e7eb" },
  studentRowActive: { backgroundColor: "#eff6ff", borderRadius: 12, paddingHorizontal: 10 }
});
