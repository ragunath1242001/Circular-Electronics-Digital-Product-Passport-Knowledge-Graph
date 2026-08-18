import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

describe("Phase 5 workspace", () => {
  beforeEach(() => {
    sessionStorage.clear();
    window.location.hash = "";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    }));
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("enters the workspace and loads the dashboard", async () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Welcome back" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: /enter workspace/i }));

    expect(await screen.findByRole("heading", { name: "Overview" })).toBeVisible();
    expect(screen.getByRole("link", { name: /Passports/ })).toBeVisible();
    expect(screen.getByRole("link", { name: /Graph & SPARQL/ })).toBeVisible();
    expect(screen.getByRole("link", { name: /Reports & governance/ })).toBeVisible();
    expect(screen.getByText("Total passports")).toBeVisible();
  });

  it("shows API failures", async () => {
    sessionStorage.setItem("dpp-demo-user", "manufacturer@example.com");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: "Graph services are unavailable." }),
    }));

    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Graph services are unavailable.");
  });

  it("applies semantic observability filters", async () => {
    sessionStorage.setItem("dpp-demo-user", "manufacturer@example.com");
    window.location.hash = "observability";
    const metrics = {
      generated_at: "2026-08-04T20:00:00Z",
      applied_filters: {},
      available_filters: {
        manufacturers: ["Eco Devices BV"], suppliers: [], models: [],
      },
      products: 4, passports: 4, validation_runs: 9, quality_score: 97.2,
      score_components: {
        completeness: 100, conformance: 88.9, provenance: 100,
        vocabulary: 100, reference_integrity: 100,
      },
      score_weights: {
        completeness: 0.3, conformance: 0.25, provenance: 0.2,
        vocabulary: 0.15, reference_integrity: 0.1,
      },
      conformance_rate: 88.9, supplier_completeness: 100,
      carbon_completeness: 100, repair_completeness: 100,
      recycling_completeness: 100, missing_mandatory_fields: 0,
      missing_provenance: 0, unknown_vocabulary_terms: 0,
      deprecated_term_usage: 0, duplicate_entity_candidates: 0,
      vocabulary_usage: [], ontology_versions: [], supplier_scores: [],
      top_failing_rules: [], validation_trend: [],
    };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => metrics });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    expect(await screen.findByRole("heading", { name: "Knowledge health" })).toBeVisible();
    fireEvent.change(screen.getByLabelText("Manufacturer"), {
      target: { value: "Eco Devices BV" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));

    await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith(
      expect.stringContaining("manufacturer=Eco+Devices+BV"),
    ));
  });

  it("renders the semantic observatory from canonical APIs", async () => {
    sessionStorage.setItem("dpp-demo-user", "manufacturer@example.com");
    window.location.hash = "overview";
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (request: string) => {
      let body: unknown = [];
      if (request.includes("ecosystem/summary")) body = {
        documents: 10_000,
        organisations: 20,
        domains: { electronics: 7000, battery: 3000 },
        ontology_versions: { "2.0.0": 8000, "1.0.0": 2000 },
        main_metrics: {
          "MET-001": 0.8, "MET-002": 0.9, "MET-005": 0.75, "MET-008": 0.6,
        },
      };
      if (request.includes("signals/summary")) body = {
        occurrences: 1000,
        by_category: { standard: 900, custom: 100 },
      };
      return { ok: true, json: async () => body };
    }));

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Ecosystem overview" })).toBeVisible();
    expect(screen.getByText("10K")).toBeVisible();
    expect(screen.getByRole("link", { name: "Ontology adoption" })).toBeVisible();
  });
});
