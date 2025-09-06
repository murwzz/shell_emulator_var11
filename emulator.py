import os
import shlex
import tkinter as tk
from tkinter import ttk

class Shell:
    def __init__(self):
        self.vfs_name = "DEMO"      
        self.cwd_parts = []         

    def parse(self, line):
        expanded = os.path.expandvars(line)
        tokens = shlex.split(expanded, posix=True)  # понимает "a b" и 'a b'
        return tokens

    def run(self, line: str) -> str:
        tokens = self.parse(line.strip())
        if not tokens:
            return ""
        cmd, *args = tokens

        if cmd == "exit":
            raise SystemExit

        if cmd == "ls":
            return f"ls args: {args}"
        if cmd == "cd":
            if len(args) != 1:
                raise ValueError("cd: expected 1 argument")
            return ""

        raise ValueError(f"unknown command: {cmd}")

class App(tk.Tk):
    def __init__(self, shell: Shell):
        super().__init__()
        self.shell = shell
        self.title(f"Shell Emulator — VFS: {shell.vfs_name}")
        self.geometry("820x520")
        self._build_ui()
        self._print_line("[ready] minimal REPL")

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
            if out:
                self._print_line(out)
        except SystemExit:
            self.destroy(); return
        except Exception as e:
            self._print_line(f"error: {e}")
        self._update_prompt()

if __name__ == "__main__":
    app = App(Shell())
    app.mainloop()
