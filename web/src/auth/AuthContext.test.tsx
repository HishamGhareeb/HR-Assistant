import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "./AuthContext";
import { api, ApiError } from "../api/client";

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>("../api/client");
  return { ...actual, api: { mintDevToken: vi.fn() } };
});

function Probe() {
  const { session, loginError, login, logout } = useAuth();
  return (
    <div>
      <div data-testid="session">{session ? `${session.tenantId}/${session.userId}` : "none"}</div>
      <div data-testid="error">{loginError ?? ""}</div>
      <button onClick={() => login("acme", "sarah").catch(() => {})}>login</button>
      <button onClick={logout}>logout</button>
    </div>
  );
}

describe("AuthContext", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.mocked(api.mintDevToken).mockReset();
  });

  it("starts with no session", () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    expect(screen.getByTestId("session")).toHaveTextContent("none");
  });

  it("logs in and persists the session to sessionStorage", async () => {
    vi.mocked(api.mintDevToken).mockResolvedValue({ access_token: "tok-1", token_type: "bearer", expires_in: 3600 });
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await userEvent.click(screen.getByText("login"));

    await waitFor(() => expect(screen.getByTestId("session")).toHaveTextContent("acme/sarah"));
    expect(sessionStorage.getItem("hr-assistant-session")).toContain("tok-1");
  });

  it("surfaces a helpful message when dev auth is disabled (404)", async () => {
    vi.mocked(api.mintDevToken).mockRejectedValue(new ApiError(404, "not found"));
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await userEvent.click(screen.getByText("login"));

    await waitFor(() => expect(screen.getByTestId("error")).toHaveTextContent(/Dev sign-in is not enabled/));
  });

  it("logs out and clears sessionStorage", async () => {
    vi.mocked(api.mintDevToken).mockResolvedValue({ access_token: "tok-1", token_type: "bearer", expires_in: 3600 });
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await userEvent.click(screen.getByText("login"));
    await waitFor(() => expect(screen.getByTestId("session")).toHaveTextContent("acme/sarah"));

    await act(async () => {
      await userEvent.click(screen.getByText("logout"));
    });

    expect(screen.getByTestId("session")).toHaveTextContent("none");
    expect(sessionStorage.getItem("hr-assistant-session")).toBeNull();
  });
});
