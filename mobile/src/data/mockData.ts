export const student = {
  id: 1,
  name: "Christian Alfredo Noriega Oliva",
  program: "Ingeniería de Sistemas",
  advisor: "Dr. Santos Fernández, Juan Pedro",
  thesisTitle: "Sistema web inteligente de gestión y predicción de desperdicio alimentario para PyMEs gastronómicas - Valle Jequetepeque 2026"
};

export const advances = [
  {
    id: 1,
    title: "Proyecto de tesis - Capítulo I",
    status: "En revisión humana",
    score: 86.4,
    grade: 17.3,
    date: "2026-04-20",
    findingsPending: 4
  },
  {
    id: 2,
    title: "Marco teórico v2",
    status: "Observado",
    score: 78.2,
    grade: 15.6,
    date: "2026-03-29",
    findingsPending: 7
  },
  {
    id: 3,
    title: "Introducción v1",
    status: "Aprobado",
    score: 91.0,
    grade: 18.2,
    date: "2026-03-10",
    findingsPending: 1
  }
];

export const findings = [
  {
    id: 1,
    severity: "Mayor",
    section: "Referencias bibliográficas",
    description: "Algunas referencias requieren verificación de DOI o ajuste de formato APA 7.",
    correction: "Revisar cada referencia y validar autor, año, título, revista y DOI.",
    example: "Apellido, A. A. (2024). Título del artículo. Revista, 12(2), 30-45. https://doi.org/..."
  },
  {
    id: 2,
    severity: "Menor",
    section: "Redacción académica",
    description: "Se recomienda mejorar conectores y evitar oraciones excesivamente extensas.",
    correction: "Dividir párrafos largos y usar conectores lógicos variados.",
    example: "Asimismo, el sistema propuesto fortalece la toma de decisiones mediante indicadores predictivos."
  },
  {
    id: 3,
    severity: "Sugerencia",
    section: "Objetivos específicos",
    description: "Los objetivos pueden alinearse mejor con los módulos del sistema.",
    correction: "Vincular cada objetivo con diagnóstico, diseño, desarrollo, implementación y evaluación.",
    example: "Diseñar la arquitectura funcional y de datos del sistema web inteligente."
  },
  {
    id: 4,
    severity: "Mayor",
    section: "Metodología",
    description: "Debe explicarse con mayor detalle el procedimiento preexperimental antes y después.",
    correction: "Precisar medición inicial, implementación, medición posterior e indicadores de comparación.",
    example: "Se aplicará una medición pretest y postest del porcentaje de desperdicio alimentario."
  }
];

export const notifications = [
  "Tu revisión IA está lista.",
  "El asesor dejó comentarios en tu avance.",
  "Quedan 3 días para la próxima entrega."
];

export const gradeHistory = [
  { version: "v1", grade: 14.2 },
  { version: "v2", grade: 15.6 },
  { version: "v3", grade: 17.3 }
];
