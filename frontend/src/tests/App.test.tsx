import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "../app/App";

describe("App", () => {
  it("mostra mensagem objetiva sem WebGL 2", () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <App webgl2={false} />
      </QueryClientProvider>,
    );
    expect(screen.getByText("WebGL 2 indisponível")).toBeInTheDocument();
  });
});
