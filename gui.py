import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import chess
import chess.pgn
from PIL import Image, ImageTk
import os
from engine import ChessEngine
from move_history import MoveHistory
from navigation import Navigation


class ChessAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chess Analyzer with Stockfish")

        self.engine = ChessEngine("stockfish/stockfish-ubuntu-x86-64-sse41-popcnt")
        self.board = chess.Board()
        self.selected_square = None
        self.piece_images = self.load_piece_images()
        self.move_stack = []
        self.setup_gui()
        self.cumulative_score = 0  # Initialize cumulative score

        self.your_moves = []  # Stack to store your moves
        self.best_moves = []  # Stack to store best moves

    def setup_gui(self):
        self.frame = tk.Frame(self.root)
        self.frame.pack(padx=10, pady=10)

        self.board_label = tk.Label(self.frame, text="Chess Board", font=("Arial", 14))
        self.board_label.grid(row=0, column=1, pady=(0, 10))

        self.board_canvas = tk.Canvas(self.frame, width=400, height=400)
        self.board_canvas.grid(row=1, column=1, rowspan=8, padx=5)

        self.analysis_area = scrolledtext.ScrolledText(self.frame, width=50, height=20)
        self.analysis_area.grid(row=1, column=2, rowspan=8, padx=10, pady=5)

        self.analysis_bar = tk.Canvas(self.frame, width=20, height=400, bg="#FFFFFF")
        self.analysis_bar.grid(row=1, column=0, rowspan=8, padx=5)

        self.load_pgn_button = tk.Button(
            self.frame, text="Load PGN", command=self.load_pgn
        )
        self.load_pgn_button.grid(row=9, column=1, columnspan=2, pady=5)

        self.reset_board_button = tk.Button(
            self.frame, text="Reset Board", command=self.reset_board
        )
        self.reset_board_button.grid(row=9, column=3, columnspan=2, pady=5)

        self.board_canvas.bind("<Button-1>", self.on_board_click)

        self.navigation = Navigation(self.frame, self.next_move, self.prev_move)
        self.navigation.frame.grid(row=10, column=1, columnspan=4, pady=5)

        self.move_history_label = tk.Label(self.frame, text="Loaded Moves", font=("Arial", 14))
        self.move_history_label.grid(row=0, column=3, pady=(0, 10))

        self.move_history = MoveHistory(self.frame)
        self.move_history.frame.grid(row=1, column=3, rowspan=8, padx=5, pady=5)

        self.loaded_moves_label = tk.Label(self.frame, text="Moves", font=("Arial", 14))
        self.loaded_moves_label.grid(row=0, column=2, pady=(0, 10))

        # Add columns for "Your Move" and "Best Move"
        self.your_move_label = tk.Label(self.frame, text="Your Move", font=("Arial", 12))
        self.your_move_label.grid(row=11, column=3, pady=(0, 5))
        
        self.best_move_label = tk.Label(self.frame, text="Best Move", font=("Arial", 12))
        self.best_move_label.grid(row=11, column=4, pady=(0, 5))

        self.your_move_listbox = tk.Listbox(self.frame, height=10)
        self.your_move_listbox.grid(row=12, column=3, pady=(0, 10))

        self.best_move_listbox = tk.Listbox(self.frame, height=10)
        self.best_move_listbox.grid(row=12, column=4, pady=(0, 10))

        self.add_board_labels()
        self.refresh_board()

    def add_board_labels(self):
        # Adding labels 'a' to 'h' at the bottom and top of the board
        for i, letter in enumerate("abcdefgh"):
            x = (i + 0.5) * 50  # Center the text within the square
            self.board_canvas.create_text(x, 405, text=letter, anchor=tk.N)
            self.board_canvas.create_text(x, -5, text=letter, anchor=tk.S)

        # Adding labels '1' to '8' on the left and right side of the board
        for i, number in enumerate("87654321"):
            y = (i + 0.5) * 50  # Center the text within the square
            self.board_canvas.create_text(-5, y, text=number, anchor=tk.E)
            self.board_canvas.create_text(405, y, text=number, anchor=tk.W)

    def load_pgn(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("PGN files", "*.pgn"), ("All files", "*.*")]
        )
        if not file_path:
            return

        with open(file_path) as f:
            game = chess.pgn.read_game(f)
            if game:
                self.board = game.board()
                self.move_stack = list(game.mainline_moves())
            else:
                messagebox.showerror("Error", "Failed to load PGN file.")
                return

        self.analysis_area.delete(1.0, tk.END)
        self.refresh_board()
        self.analyze_current_position()
        self.move_history.update(self.move_stack)
        self.update_analysis_bar()

    def reset_board(self):
        self.board.reset()
        self.move_stack = []
        self.analysis_area.delete(1.0, tk.END)
        self.cumulative_score = 0  # Reset cumulative score
        self.your_moves.clear()
        self.best_moves.clear()
        self.your_move_listbox.delete(0, tk.END)
        self.best_move_listbox.delete(0, tk.END)
        self.refresh_board()
        self.move_history.update(self.move_stack)
        self.update_analysis_bar()

    def on_board_click(self, event):
        x, y = event.x, event.y
        col = x // 50
        row = 7 - (y // 50)
        square = chess.square(col, row)

        if self.selected_square is None:
            if self.board.piece_at(square):
                self.selected_square = square
        else:
            move = chess.Move(self.selected_square, square)
            if move in self.board.legal_moves:
                self.board.push(move)
                self.selected_square = None
                self.refresh_board()
                self.analyze_current_position()
                self.move_history.update(self.board.move_stack)
                self.update_analysis_bar()
            else:
                self.selected_square = None

    def analyze_current_position(self):
        analysis = self.engine.analyze(self.board)
        self.analysis_area.delete(1.0, tk.END)
        if self.board.move_stack:
            self.analysis_area.insert(tk.END, f"Move: {self.board.peek()}\n")
            self.your_moves.append(str(self.board.peek()))
            self.your_move_listbox.insert(tk.END, str(self.board.peek()))
        self.analysis_area.insert(tk.END, f"Score: {analysis['score']}\n")
        if "pv" in analysis:
            self.analysis_area.insert(tk.END, f"Best Move: {analysis['pv'][0]}\n\n")
            self.best_moves.append(str(analysis['pv'][0]))
            self.best_move_listbox.insert(tk.END, str(analysis['pv'][0]))

    def refresh_board(self):
        self.board_canvas.delete("all")
        # Draw the board and pieces
        for square in chess.SQUARES:
            col, row = chess.square_file(square), chess.square_rank(square)
            x1, y1 = col * 50, (7 - row) * 50
            x2, y2 = x1 + 50, y1 + 50
            color = "#F0D9B5" if (col + row) % 2 == 0 else "#B58863"
            self.board_canvas.create_rectangle(x1, y1, x2, y2, fill=color)
            piece = self.board.piece_at(square)
            if piece:
                piece_image = self.piece_images[piece.symbol()]
                self.board_canvas.create_image(x1, y1, anchor=tk.NW, image=piece_image)

        # Highlight the last move played
        if self.board.move_stack:
            last_move = self.board.move_stack[-1]
            self.highlight_move(last_move, color="#FFA500")  # Grey color for the last move

        # Highlight the best move
        best_move = self.get_best_move()
        if best_move:
            self.highlight_move(best_move, color="#00FF00")  # Green color for the best move

        self.add_board_labels()

    def highlight_move(self, move, color):
        from_square = move.from_square
        to_square = move.to_square
        from_col, from_row = chess.square_file(from_square), chess.square_rank(from_square)
        to_col, to_row = chess.square_file(to_square), chess.square_rank(to_square)
        self.board_canvas.create_rectangle(from_col * 50, (7 - from_row) * 50, (from_col + 1) * 50, (7 - from_row + 1) * 50, outline=color, width=3)
        self.board_canvas.create_rectangle(to_col * 50, (7 - to_row) * 50, (to_col + 1) * 50, (7 - to_row + 1) * 50, outline=color, width=3)

    def get_best_move(self):
        analysis = self.engine.analyze(self.board)
        if "pv" in analysis:
            return analysis["pv"][0]
        return None

    def load_piece_images(self):
        piece_symbols = {
            "P": "wp.png",
            "N": "wn.png",
            "B": "wb.png",
            "R": "wr.png",
            "Q": "wq.png",
            "K": "wk.png",
            "p": "bp.png",
            "n": "bn.png",
            "b": "bb.png",
            "r": "br.png",
            "q": "bq.png",
            "k": "bk.png",
        }
        piece_images = {}
        for symbol, filename in piece_symbols.items():
            image = Image.open(f"assets/piece_images/{filename}")
            piece_images[symbol] = ImageTk.PhotoImage(image.resize((50, 50)))
        return piece_images

    def on_quit(self):
        self.engine.quit()
        self.root.destroy()

    def next_move(self):
        if self.move_stack:
            move = self.move_stack.pop(0)
            self.board.push(move)
            self.refresh_board()
            self.analyze_current_position()
            self.move_history.update(self.board.move_stack)
            self.update_analysis_bar()

    def prev_move(self):
        if self.board.move_stack:
            move = self.board.pop()
            self.move_stack.insert(0, move)
            self.refresh_board()
            self.analyze_current_position()
            self.move_history.update(self.board.move_stack)
            self.update_analysis_bar()

    def update_analysis_bar(self):
        analysis = self.engine.analyze(self.board)
        score = analysis["score"]

        if isinstance(score, int):
            # Handle integer score directly from Stockfish
            normalized_score = score / 100  # Adjust as per Stockfish score range
        else:
            # Handle score object from Stockfish
            normalized_score = score.relative.score()

        max_score = 10  # Adjust maximum score based on Stockfish output
        if normalized_score > 1:
            normalized_score = 1
        elif normalized_score < -1:
            normalized_score = -1

        # Calculate percentages of advantage for white and black
        white_percentage = (normalized_score + 1) * 50
        black_percentage = 100 - white_percentage

        # Clear existing bar
        self.analysis_bar.delete("all")

        # Draw white and black sections of the bar
        self.analysis_bar.create_rectangle(
            0, 0, 20, white_percentage * 4, fill="#FFFFFF", outline=""
        )
        self.analysis_bar.create_rectangle(
            0, white_percentage * 4, 20, 400, fill="#000000", outline=""
        )

        # Optionally, draw a divider line (uncomment if needed)
        # self.analysis_bar.create_line(0, 200, 20, 200, fill="gray")

        self.analysis_bar.update()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)
        self.root.mainloop()

