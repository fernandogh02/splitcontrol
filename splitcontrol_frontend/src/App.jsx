import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import CreateGroup from "./pages/CreateGroup";
import ExpenseSummary from "./pages/ExpenseSummary";
import PrivateRoute from "./components/PrivateRoute";
import GroupDetail from "./pages/GroupDetail";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" />} />

        <Route path="/login" element={<Login />} />
        <Route path="/registro" element={<Register />} />

        <Route
          path="/dashboard"
          element={
            <PrivateRoute>
              <Dashboard />
            </PrivateRoute>
          }
        />

        <Route
          path="/grupos/crear"
          element={
            <PrivateRoute>
              <CreateGroup />
            </PrivateRoute>
          }
        />

        <Route
          path="/resumen"
          element={
            <PrivateRoute>
              <ExpenseSummary />
            </PrivateRoute>
          }
        />

        <Route
          path="/grupos/:id"
           element={
             <PrivateRoute>
                <GroupDetail />
              </PrivateRoute>
          }
        />

      </Routes>
    </BrowserRouter>
  );
}

export default App;