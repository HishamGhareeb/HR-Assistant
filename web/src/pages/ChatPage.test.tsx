import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ChatPage } from "./ChatPage";
import { api } from "../api/client";

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>("../api/client");
  return { ...actual, api: { askQuestion: vi.fn(), submitFeedback: vi.fn() } };
});

function renderWithSession() {
  sessionStorage.setItem(
    "hr-assistant-session",
    JSON.stringify({ tenantId: "demo-org", userId: "priya", token: "tok-1", expiresAt: Date.now() + 3600_000 }),
  );
  return render(
    <AuthProvider>
      <ChatPage />
    </AuthProvider>,
  );
}

describe("ChatPage", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.mocked(api.askQuestion).mockReset();
    vi.mocked(api.submitFeedback).mockReset();
  });

  it("shows the empty state before any question is asked", () => {
    renderWithSession();
    expect(screen.getByText(/Ask something like/)).toBeInTheDocument();
  });

  it("asks a question and renders the answer", async () => {
    vi.mocked(api.askQuestion).mockResolvedValue({
      answer: "You have 30 days of annual leave.",
      suggestions: [],
      blocked: false,
      request_id: "req-1",
    });
    renderWithSession();

    await userEvent.type(screen.getByLabelText("Question"), "How much leave do I get?");
    await userEvent.click(screen.getByText("Ask"));

    await waitFor(() => expect(screen.getByText("You have 30 days of annual leave.")).toBeInTheDocument());
    expect(api.askQuestion).toHaveBeenCalledWith("tok-1", { question: "How much leave do I get?" });
  });

  it("renders suggestions attached to an answer", async () => {
    vi.mocked(api.askQuestion).mockResolvedValue({
      answer: "Noted.",
      suggestions: [{ category: "leave_expiring", reasoning: "Carried-over leave expires soon.", record_reference: "LEAVE-1" }],
      blocked: false,
      request_id: "req-2",
    });
    renderWithSession();

    await userEvent.type(screen.getByLabelText("Question"), "q");
    await userEvent.click(screen.getByText("Ask"));

    await waitFor(() => expect(screen.getByText("Carried-over leave expires soon.")).toBeInTheDocument());
    expect(screen.getByText(/leave expiring/)).toBeInTheDocument();
  });

  it("visually flags a blocked response", async () => {
    vi.mocked(api.askQuestion).mockResolvedValue({
      answer: "That response was flagged by an automated safety check and held for review.",
      suggestions: [],
      blocked: true,
      request_id: "req-3",
    });
    renderWithSession();

    await userEvent.type(screen.getByLabelText("Question"), "q");
    await userEvent.click(screen.getByText("Ask"));

    await waitFor(() => expect(screen.getByText(/held by the output safety scanner/i)).toBeInTheDocument());
  });

  it("submits helpful feedback with one click", async () => {
    vi.mocked(api.askQuestion).mockResolvedValue({ answer: "ok", suggestions: [], blocked: false, request_id: "req-4" });
    vi.mocked(api.submitFeedback).mockResolvedValue({
      feedback_id: "fb-1",
      tenant_id: "demo-org",
      user_id: "priya",
      request_id: "req-4",
      question: "q",
      answer: "ok",
      helpful: true,
      reason_code: null,
      note: null,
      escalated: false,
      resolved: false,
      resolution: null,
      created_at: new Date().toISOString(),
    });
    renderWithSession();

    await userEvent.type(screen.getByLabelText("Question"), "q");
    await userEvent.click(screen.getByText("Ask"));
    await waitFor(() => expect(screen.getByLabelText("Helpful")).toBeInTheDocument());

    await userEvent.click(screen.getByLabelText("Helpful"));

    await waitFor(() => expect(screen.getByText("Thanks for the feedback.")).toBeInTheDocument());
    expect(api.submitFeedback).toHaveBeenCalledWith(
      "tok-1",
      "req-4",
      expect.objectContaining({ helpful: true, question: "q", answer: "ok" }),
    );
  });

  it("requires a reason code before submitting not-helpful feedback", async () => {
    vi.mocked(api.askQuestion).mockResolvedValue({ answer: "ok", suggestions: [], blocked: false, request_id: "req-5" });
    vi.mocked(api.submitFeedback).mockResolvedValue({
      feedback_id: "fb-2",
      tenant_id: "demo-org",
      user_id: "priya",
      request_id: "req-5",
      question: "q",
      answer: "ok",
      helpful: false,
      reason_code: "incomplete",
      note: null,
      escalated: true,
      resolved: false,
      resolution: null,
      created_at: new Date().toISOString(),
    });
    renderWithSession();

    await userEvent.type(screen.getByLabelText("Question"), "q");
    await userEvent.click(screen.getByText("Ask"));
    await waitFor(() => expect(screen.getByLabelText("Not helpful")).toBeInTheDocument());

    await userEvent.click(screen.getByLabelText("Not helpful"));
    expect(api.submitFeedback).not.toHaveBeenCalled();

    await userEvent.click(screen.getByText("Submit"));

    await waitFor(() => expect(screen.getByText("Thanks — flagged for HR review.")).toBeInTheDocument());
    expect(api.submitFeedback).toHaveBeenCalledWith(
      "tok-1",
      "req-5",
      expect.objectContaining({ helpful: false, reason_code: "incomplete" }),
    );
  });
});
