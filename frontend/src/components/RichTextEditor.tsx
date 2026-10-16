import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useEffect } from "react";

/** Output is re-sanitised on the server (allow-list); this is authoring convenience only. */
export function RichTextEditor({ value, onChange, label }: { value: string; onChange: (html: string) => void; label: string }) {
  const editor = useEditor({
    extensions: [StarterKit.configure({ link: { openOnClick: false } })],
    content: value,
    onUpdate: ({ editor }) => onChange(editor.isEmpty ? "" : editor.getHTML()),
    editorProps: {
      attributes: {
        role: "textbox",
        "aria-multiline": "true",
        "aria-label": label,
        class: "prose-notice min-h-48 px-3 py-2 focus:outline-none",
      },
    },
  });

  useEffect(() => {
    if (editor && value !== editor.getHTML() && !(value === "" && editor.isEmpty)) {
      editor.commands.setContent(value, { emitUpdate: false });
    }
  }, [value, editor]);

  if (!editor) return null;
  const btn = (name: string, active: boolean, run: () => void) => (
    <button
      type="button"
      aria-pressed={active}
      onClick={run}
      className={`rounded px-2 py-1 text-sm ${active ? "bg-brand-100 text-brand-800" : "text-[#333333] hover:bg-black/5"}`}
    >
      {name}
    </button>
  );
  return (
    <div className="rounded-[11px] border border-hairline bg-white focus-within:border-brand-600">
      <div className="flex flex-wrap gap-1 border-b border-hairline p-1.5" role="toolbar" aria-label="Formatting">
        {btn("Bold", editor.isActive("bold"), () => editor.chain().focus().toggleBold().run())}
        {btn("Italic", editor.isActive("italic"), () => editor.chain().focus().toggleItalic().run())}
        {btn("Heading", editor.isActive("heading", { level: 2 }), () => editor.chain().focus().toggleHeading({ level: 2 }).run())}
        {btn("Bullets", editor.isActive("bulletList"), () => editor.chain().focus().toggleBulletList().run())}
        {btn("Numbered", editor.isActive("orderedList"), () => editor.chain().focus().toggleOrderedList().run())}
        {btn("Link", editor.isActive("link"), () => {
          if (editor.isActive("link")) return editor.chain().focus().unsetLink().run();
          const href = window.prompt("Link address (https://…)");
          if (href) editor.chain().focus().setLink({ href }).run();
        })}
      </div>
      <EditorContent editor={editor} />
    </div>
  );
}
