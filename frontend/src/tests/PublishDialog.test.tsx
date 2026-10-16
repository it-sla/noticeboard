import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PublishDialog } from "../components/PublishDialog";
import type { Preview } from "../types";

const preview: Preview = {
  subject: "Dashain holiday",
  html: "<p>x</p>",
  text: "x",
  sender: "Shangri La Tours <it@gohimalaya.travel>",
  recipient_count: 42,
  attachments: [],
  broadcast_enabled: true,
  email_mode: "smtp",
};

describe("PublishDialog", () => {
  it("shows the exact recipient count and requires explicit acknowledgement", async () => {
    const onConfirm = vi.fn();
    render(<PublishDialog open preview={preview} busy={false} onConfirm={onConfirm} onClose={() => {}} />);
    expect(screen.getByText("42 active employees")).toBeInTheDocument();
    expect(screen.getByText(/it@gohimalaya\.travel/)).toBeInTheDocument();
    const publish = screen.getByRole("button", { name: /publish & email 42/i });
    expect(publish).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox"));
    expect(publish).toBeEnabled();
    await userEvent.click(publish);
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("blocks publishing while broadcasting is disabled", async () => {
    render(<PublishDialog open preview={{ ...preview, broadcast_enabled: false }} busy={false} onConfirm={() => {}} onClose={() => {}} />);
    await userEvent.click(screen.getByRole("checkbox"));
    expect(screen.getByRole("button", { name: /publish & email/i })).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent(/disabled/i);
  });

  it("warns in dry-run mode", () => {
    render(<PublishDialog open preview={{ ...preview, email_mode: "dry_run" }} busy={false} onConfirm={() => {}} onClose={() => {}} />);
    expect(screen.getByText(/dry-run mode/i)).toBeInTheDocument();
  });
});
