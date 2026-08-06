import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import { AuthProvider } from "../auth/AuthContext";
import { PayrollPage } from "./PayrollPage";

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>("../api/client");
  return {
    ...actual,
    api: {
      calculateSioContribution: vi.fn(),
      calculateEosbMonthlyContribution: vi.fn(),
      calculateEosbGratuity: vi.fn(),
      validateWpsSalaryFile: vi.fn(),
    },
  };
});

function renderWithSession() {
  sessionStorage.setItem(
    "hr-assistant-session",
    JSON.stringify({ tenantId: "demo-org", userId: "hr-demo", token: "tok-1", expiresAt: Date.now() + 3600_000 }),
  );
  return render(
    <AuthProvider>
      <PayrollPage />
    </AuthProvider>,
  );
}

describe("PayrollPage", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.mocked(api.calculateSioContribution).mockReset();
    vi.mocked(api.calculateEosbMonthlyContribution).mockReset();
    vi.mocked(api.calculateEosbGratuity).mockReset();
    vi.mocked(api.validateWpsSalaryFile).mockReset();
  });

  it("calculates SIO contributions through the backend and renders citations", async () => {
    vi.mocked(api.calculateSioContribution).mockResolvedValue({
      supported: true,
      unsupported: null,
      result: {
        worker_category: "bahraini_private_sector",
        branch: "pension",
        payer: "employee",
        rate_percent: "7",
        monthly_wage: "1000",
        amount: "70.000",
        rate_code: "BH-SIO-PENSION-EMPLOYEE-2023",
        note: null,
        figure: {
          name: "Bahraini private-sector pension employee share",
          value: "7",
          unit: "percent",
          note: null,
          citation: {
            section: "HIS-60",
            instrument: "Law No. (14) of 2022",
            retrieved: "2026-08-03",
            source_doc: "docs/BAHRAIN_PAYROLL_SOURCES.md",
            quote: null,
          },
        },
      },
    });

    renderWithSession();
    await userEvent.click(screen.getByText("Calculate contribution"));

    await waitFor(() => expect(screen.getByText("BHD 70.000")).toBeInTheDocument());
    expect(screen.getByText(/Law No\. \(14\) of 2022/)).toBeInTheDocument();
    expect(api.calculateSioContribution).toHaveBeenCalledWith(
      "tok-1",
      expect.objectContaining({
        worker_category: "bahraini_private_sector",
        branch: "pension",
        payer: "employee",
      }),
    );
  });

  it("shows unsupported payroll combinations as HR-review states", async () => {
    vi.mocked(api.calculateSioContribution).mockResolvedValue({
      supported: false,
      result: null,
      unsupported: {
        code: "no_source_backed_rate",
        message: "No source-backed rate exists for this combination.",
        requires_hr_review: true,
      },
    });

    renderWithSession();
    await userEvent.click(screen.getByText("Calculate contribution"));

    await waitFor(() => expect(screen.getByText("Not calculated.")).toBeInTheDocument());
    expect(screen.getByText(/No source-backed rate exists/)).toBeInTheDocument();
  });
});
