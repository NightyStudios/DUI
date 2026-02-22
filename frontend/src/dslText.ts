export function starterDslSource(surfaceId: string): string {
  return `surface ${surfaceId} {
  surface_meta { title: "Математическая панель" route: "/dashboard" }

  theme {
    profile: default
    density: comfortable
    tokens { accent: "#0c7bf2" }
  }

  layout_constraints {
    max_columns: 2
    sidebar_width: normal
    content_density: comfortable
  }

  node root: layout.page {
    children: [main_header, main_content, main_sidebar, main_footer]
  }

  node main_header: layout.region {
    props { zone: header }
    children: [course_progress]
  }

  node main_content: layout.region {
    props { zone: content }
    children: [learning_overview]
  }

  node learning_overview: layout.section {
    props { title: "Обзор обучения" zone: content }
    layout { columns: 2 }
    children: [learning_path, mastery_trend]
  }

  node main_sidebar: layout.region {
    props { zone: sidebar }
    children: [practice_queue]
  }

  node main_footer: layout.region {
    props { zone: footer }
    children: []
  }

  node course_progress: data.kpi_card {
    props { title: "Прогресс курса" zone: header capability_id: math.progress_overview protected: true }
  }

  node learning_path: data.data_table {
    props { title: "Траектория обучения" zone: content capability_id: math.learning_path }
  }

  node mastery_trend: chart.line {
    props { title: "Динамика освоения" zone: content capability_id: math.mastery_trend }
  }

  node practice_queue: data.activity_feed {
    props { title: "Очередь практики" zone: sidebar capability_id: math.practice_queue }
  }
}
`;
}
