import os, sys, shlex, argparse, tkinter as tk
from tkinter import ttk, messagebox

class Shell:
    def __init__(self, vfs_name="DEMO"):
        self.vfs_name = vfs_name
        self.cwd_parts = []

    def parse(self, line):
        return shlex.split(os.path.expandvars(line), posix=True)

    def run(self, line: str) -> str:
        tokens = self.parse(line.strip())
        if not tokens: return ""
        cmd, *args = tokens
        if cmd == "exit": raise SystemExit
        if cmd == "ls":   return f"ls args: {args}"
        if cmd == "cd":
            if len(args) != 1: raise ValueError("cd: expected 1 argument")
            return ""
        raise ValueError(f"unknown command: {cmd}")

class App(tk.Tk):
    def __init__(self, shell: Shell):
        super().__init__()
        self.shell = shell
        self.title(f"Shell Emulator — VFS: {shell.vfs_name}")
        self.geometry("820x520")
        self._build_ui()
        self._print_line("[ready] with --script support")

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.text = tk.Text(self, wrap='word', state='disabled', font=('Menlo', 12))
        self.text.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 4))
        self.input = ttk.Entry(self)
        self.input.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.input.bind("<Return>", self._on_enter)
        self._update_prompt()

    def _prompt(self) -> str:
        path = '/' + '/'.join(self.shell.cwd_parts)
        return f"{self.shell.vfs_name}:{path}$ "

    def _update_prompt(self):
        p = self._prompt()
        self.input.delete(0, tk.END)
        self.input.insert(0, p)
        self.input.icursor(len(p))

    def _print_line(self, s: str):
        self.text.configure(state='normal')
        self.text.insert(tk.END, s + "\n")
        self.text.see(tk.END)
        self.text.configure(state='disabled')

    def _on_enter(self, _=None):
        full = self.input.get()
        cmd = full.split("$ ", 1)[1] if "$ " in full else full
        self._print_line(full)
        try:
            out = self.shell.run(cmd)
            if out: self._print_line(out)
        except SystemExit:
            self.destroy(); return
        except Exception as e:
            self._print_line(f"error: {e}")
        self._update_prompt()

    def run_script(self, lines):
        for raw in lines:
            line = raw.rstrip("\n")
            if not line.strip():  
                continue
            self._print_line(self._prompt() + line)
            try:
                out = self.shell.run(line)
                if out: self._print_line(out)
            except SystemExit:
                self.destroy(); return
            except Exception as e:
                self._print_line(f"error: {e}")
                break
        self._update_prompt()

def main(argv=None):
    parser = argparse.ArgumentParser(description="GUI Shell Emulator (stage 2)")
    parser.add_argument("--vfs", help="путь к VFS (пока не используем)")
    parser.add_argument("--script", help="путь к стартовому скрипту")
    parser.add_argument("--vfs-name", help="имя VFS в заголовке", default="DEMO")
    args = parser.parse_args(argv)

    print(f"[startup] argv={sys.argv} parsed={{'vfs': {args.vfs!r}, 'script': {args.script!r}, 'vfs_name': {args.vfs_name!r}}}")

    app = App(Shell(vfs_name=args.vfs_name))

    if args.script:
        try:
            with open(args.script, encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            messagebox.showerror("Script error", f"Failed to read script: {e}")
            sys.exit(3)
        app.after(200, lambda: app.run_script(lines))

    app.mainloop()

if __name__ == "__main__":
    main()

