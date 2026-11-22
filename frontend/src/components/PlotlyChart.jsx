import Plotly from "plotly.js-basic-dist-min";
import createPlotlyComponent from "react-plotly.js/factory";

// Using the small "basic" Plotly bundle (line + bar charts) keeps the app fast.
const Plot = createPlotlyComponent(Plotly);

// Dark-theme layout shared by every chart
export default function PlotlyChart({ title, data, yTitle, yRange, shapes, barmode }) {
  const layout = {
    title: { text: title, font: { size: 15, color: "#e8e9ff" } },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: "#b9bcf0" },
    margin: { t: 45, r: 20, b: 50, l: 55 },
    xaxis: { title: "Hour of day", dtick: 2, gridcolor: "rgba(255,255,255,0.08)" },
    yaxis: { title: yTitle, range: yRange, gridcolor: "rgba(255,255,255,0.08)", zeroline: false },
    legend: { orientation: "h", y: -0.28 },
    shapes,
    barmode,
  };
  return (
    <Plot
      data={data}
      layout={layout}
      config={{ displayModeBar: false, responsive: true }}
      useResizeHandler
      style={{ width: "100%", height: "320px" }}
    />
  );
}
