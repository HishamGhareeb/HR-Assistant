import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { PersonaLoginPage } from "./auth/PersonaLoginPage";
import { Layout } from "./components/Layout";
import { ChatPage } from "./pages/ChatPage";
import { SuggestionsPage } from "./pages/SuggestionsPage";
import { AdminPage } from "./pages/AdminPage";
import { FeedbackPage } from "./pages/FeedbackPage";
import { PayrollPage } from "./pages/PayrollPage";

function AppRoutes() {
  const { session } = useAuth();

  if (!session) {
    return <PersonaLoginPage />;
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/suggestions" element={<SuggestionsPage />} />
        <Route path="/feedback" element={<FeedbackPage />} />
        <Route path="/payroll" element={<PayrollPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Route>
    </Routes>
  );
}

export function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
