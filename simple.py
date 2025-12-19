import sys
import os
import json
import vlc
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

class EnhancedAudioPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Add seek throttling variables
        self.last_seek_time = 0
        self.seek_throttle_ms = 100  # Minimum 100ms between seeks
        self.pending_seek = None
        
        # Initialize VLC player
        self.player = vlc.MediaPlayer()
        self.bookmarks_file = "bookmarks.json"
        self.current_file = ""
        
        # Folder inside your project
        self.audio_folder = "audio_files"  
        
        # Ensure the folder exists
        if not os.path.exists(self.audio_folder):
            os.makedirs(self.audio_folder)

        # Set initial volume
        self.player.audio_set_volume(50)
        
        self.init_ui()
        self.create_actions()
        self.create_menu()
        self.load_bookmarks()
        
    def init_ui(self):
        """Initialize the user interface"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # ===== File selection section =====
        file_group = QGroupBox("Audio File")
        file_layout = QVBoxLayout(file_group)
        
        file_select_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("border: 1px solid #ccc; padding: 5px;")
        self.file_btn = QPushButton("Select Audio File")
        self.file_btn.clicked.connect(self.select_file)
        
        file_select_layout.addWidget(self.file_btn)
        file_select_layout.addWidget(self.file_label, 1)
        file_layout.addLayout(file_select_layout)
        
        main_layout.addWidget(file_group)
        
        # ===== Progress section =====
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Time display
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("00:00")
        self.current_time_label.setAlignment(Qt.AlignCenter)
        self.current_time_label.setMinimumWidth(60)
        
        self.total_time_label = QLabel("00:00")
        self.total_time_label.setAlignment(Qt.AlignCenter)
        self.total_time_label.setMinimumWidth(60)
        
        # Progress slider
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.sliderMoved.connect(self.seek_audio)
        self.progress_slider.setEnabled(False)
        
        time_layout.addWidget(self.current_time_label)
        time_layout.addWidget(self.progress_slider, 1)
        time_layout.addWidget(self.total_time_label)
        progress_layout.addLayout(time_layout)
        
        main_layout.addWidget(progress_group)
        
        # ===== Controls section =====
        controls_group = QGroupBox("Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        # Single play/pause toggle button
        self.play_pause_btn = QPushButton("▶ Play")
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.play_pause_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self.stop_audio)
        self.stop_btn.setEnabled(False)
        
        # Bookmark button
        self.bookmark_btn = QPushButton("🔖 Add Bookmark")
        self.bookmark_btn.clicked.connect(self.add_bookmark)
        self.bookmark_btn.setEnabled(False)
        
        # Volume control
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("🔊"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self.set_volume)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addStretch()
        
        controls_layout.addWidget(self.play_pause_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.bookmark_btn)
        controls_layout.addLayout(volume_layout)
        
        main_layout.addWidget(controls_group)
        
        # ===== Bookmarks section =====
        bookmarks_group = QGroupBox("Bookmarks")
        bookmarks_layout = QVBoxLayout(bookmarks_group)
        
        # Bookmarks list
        self.bookmarks_list = QListWidget()
        self.bookmarks_list.itemDoubleClicked.connect(self.play_from_bookmark)
        bookmarks_layout.addWidget(self.bookmarks_list)
        self.bookmarks_list.itemSelectionChanged.connect(self.update_bookmark_buttons_state)
        
        # Bookmark management buttons
        bookmark_buttons_layout = QHBoxLayout()
        self.clear_bookmarks_btn = QPushButton("Clear All Bookmarks")
        self.clear_bookmarks_btn.clicked.connect(self.clear_bookmarks)
        self.delete_bookmark_btn = QPushButton("Delete Selected")
        self.delete_bookmark_btn.clicked.connect(self.delete_selected_bookmark)

        # Add Edit button
        self.edit_bookmark_btn = QPushButton("Edit Selected")
        self.edit_bookmark_btn.clicked.connect(self.edit_selected_bookmark)
        self.edit_bookmark_btn.setEnabled(False)  # Disabled by default

        bookmark_buttons_layout.addWidget(self.clear_bookmarks_btn)
        bookmark_buttons_layout.addWidget(self.delete_bookmark_btn)
        bookmark_buttons_layout.addWidget(self.edit_bookmark_btn)
        bookmark_buttons_layout.addStretch()
        
        bookmarks_layout.addLayout(bookmark_buttons_layout)
        
        main_layout.addWidget(bookmarks_group, 1)
        
        # ===== Status bar =====
        self.statusBar().showMessage("Ready")
        
        # Timer to update time and progress
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(100)  # Update every 100ms
        
    def create_actions(self):
        """Create keyboard shortcuts"""
        # Play/Pause toggle with Space
        self.play_pause_action = QAction(self)
        self.play_pause_action.setShortcut("Space")
        self.play_pause_action.triggered.connect(self.toggle_play_pause)
        self.addAction(self.play_pause_action)
        
        # Add bookmark with B
        self.bookmark_action = QAction(self)
        self.bookmark_action.setShortcut("B")
        self.bookmark_action.triggered.connect(self.add_bookmark)
        self.addAction(self.bookmark_action)
        
        # Stop with S
        self.stop_action = QAction(self)
        self.stop_action.setShortcut("S")
        self.stop_action.triggered.connect(self.stop_audio)
        self.addAction(self.stop_action)

        # Edit Bookmark with E
        self.edit_action = QAction(self)
        self.edit_action.setShortcut("E")
        self.edit_action.triggered.connect(self.edit_selected_bookmark)
        self.addAction(self.edit_action)
        
        # Seek forward with Right arrow
        self.seek_forward_action = QAction(self)
        self.seek_forward_action.setShortcut(Qt.Key_Right)
        self.seek_forward_action.triggered.connect(lambda: self.seek_relative(5000))
        self.addAction(self.seek_forward_action)
        
        # Seek backward with Left arrow
        self.seek_backward_action = QAction(self)
        self.seek_backward_action.setShortcut(Qt.Key_Left)
        self.seek_backward_action.triggered.connect(lambda: self.seek_relative(-5000))
        self.addAction(self.seek_backward_action)
        
    def create_menu(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open Audio File", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.select_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Bookmarks menu
        bookmarks_menu = menubar.addMenu("Bookmarks")

        add_bookmark_action = QAction("Add Bookmark", self)
        add_bookmark_action.setShortcut("Ctrl+B")
        add_bookmark_action.triggered.connect(self.add_bookmark)
        bookmarks_menu.addAction(add_bookmark_action)

        # Add Edit Bookmark menu item
        edit_bookmark_action = QAction("Edit Selected Bookmark", self)
        edit_bookmark_action.setShortcut("Ctrl+E")
        edit_bookmark_action.triggered.connect(self.edit_selected_bookmark)
        bookmarks_menu.addAction(edit_bookmark_action)

        clear_bookmarks_action = QAction("Clear All Bookmarks", self)
        clear_bookmarks_action.triggered.connect(self.clear_bookmarks)
        bookmarks_menu.addAction(clear_bookmarks_action)
        
    def select_file(self):
        """Open file dialog to select audio file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            self.audio_folder,
            "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.wma);;All Files (*.*)"
        )
        
        if file_path:
            self.load_audio_file(file_path)
            
    def load_audio_file(self, file_path):
        """Load and prepare audio file for playback, and copy it to project folder if needed"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            filename = os.path.basename(file_path)
            
            # Check if file is already in the project audio folder
            file_in_project_folder = os.path.commonpath([os.path.abspath(file_path), os.path.abspath(self.audio_folder)]) == os.path.abspath(self.audio_folder)
            
            if file_in_project_folder:
                # File is already in project folder, use it directly
                self.current_file = file_path
                self.statusBar().showMessage(f"Loaded from project folder: {filename}", 3000)
            else:
                # Copy file to project audio folder
                destination_path = os.path.join(self.audio_folder, filename)
                
                # Check if file already exists in destination
                if os.path.exists(destination_path):
                    # Ask user what to do
                    reply = QMessageBox.question(
                        self,
                        "File Exists",
                        f"'{filename}' already exists in the project folder.\n\n"
                        f"Would you like to:\n"
                        f"• Use existing file (Recommended)\n"
                        f"• Overwrite with new file\n"
                        f"• Cancel",
                        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                    )
                    
                    if reply == QMessageBox.Cancel:
                        return  # User canceled
                    elif reply == QMessageBox.Yes:
                        # Use existing file in project folder
                        self.current_file = destination_path
                        self.statusBar().showMessage(f"Using existing file in project folder: {filename}", 3000)
                    else:  # QMessageBox.No - Overwrite
                        try:
                            import shutil
                            shutil.copy2(file_path, destination_path)
                            self.current_file = destination_path
                            self.statusBar().showMessage(f"Overwritten in project folder: {filename}", 3000)
                        except Exception as copy_error:
                            QMessageBox.warning(
                                self, 
                                "Copy Failed", 
                                f"Could not overwrite file:\n{str(copy_error)}\n"
                                f"Will use original file location instead."
                            )
                            self.current_file = file_path
                else:
                    # Copy the file (new file)
                    try:
                        import shutil
                        shutil.copy2(file_path, destination_path)
                        self.current_file = destination_path
                        self.statusBar().showMessage(f"Copied to project folder: {filename}", 3000)
                    except Exception as copy_error:
                        QMessageBox.warning(
                            self, 
                            "Copy Failed", 
                            f"Could not copy file to project folder:\n{str(copy_error)}\n"
                            f"Will use original file location instead."
                        )
                        # Use original file path if copy fails
                        self.current_file = file_path
            
            self.file_label.setText(filename)
            
            # Load media
            media = vlc.Media(self.current_file)
            self.player.set_media(media)
            
            # Enable controls
            self.play_pause_btn.setEnabled(True)
            self.play_pause_btn.setText("▶ Play")
            self.stop_btn.setEnabled(True)
            self.bookmark_btn.setEnabled(True)
            self.progress_slider.setEnabled(True)
            
            # Reset display
            self.current_time_label.setText("00:00")
            self.total_time_label.setText("00:00")
            self.progress_slider.setValue(0)
            
            # Update status
            self.statusBar().showMessage(f"Loaded: {filename}", 3000)
            
            # Get total duration after a short delay
            QTimer.singleShot(100, self.update_total_time)
            
        except FileNotFoundError as e:
            QMessageBox.warning(self, "File Not Found", str(e))
            self.reset_player()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")
            self.reset_player()
            
    def update_total_time(self):
        """Update the total time display"""
        if self.player.get_media():
            length_ms = self.player.get_length()
            if length_ms > 0:
                seconds = length_ms // 1000
                self.total_time_label.setText(f"{seconds // 60:02d}:{seconds % 60:02d}")
                
    def toggle_play_pause(self):
        """Toggle between play and pause"""
        if self.player.is_playing():
            self.player.pause()
            self.play_pause_btn.setText("▶ Play")  # Change to Play icon
            self.statusBar().showMessage("Paused", 2000)
        else:
            if self.current_file:
                self.player.play()
                self.play_pause_btn.setText("⏸ Pause")  # Change to Pause icon
                self.statusBar().showMessage("Playing", 2000)
            
    def stop_audio(self):
        """Stop audio playback"""
        self.player.stop()
        self.current_time_label.setText("00:00")
        self.progress_slider.setValue(0)
        self.play_pause_btn.setText("▶ Play")  # Reset to Play when stopped
        self.statusBar().showMessage("Stopped", 2000)
        
    def update_time(self):
        """Update current time and progress slider"""
        if self.player.get_media():
            ms = self.player.get_time()
            length = self.player.get_length()
            
            if ms >= 0:
                # Update time label
                seconds = ms // 1000
                self.current_time_label.setText(f"{seconds // 60:02d}:{seconds % 60:02d}")
                
                # Update progress slider
                if length > 0:
                    progress = int((ms / length) * 1000)
                    if not self.progress_slider.isSliderDown():  # Only update if user isn't dragging
                        self.progress_slider.setValue(progress)
                        
    def seek_audio(self, position):
        """Seek to specific position in audio with throttling"""
        if not self.player.get_media():
            return
        
        current_time = QDateTime.currentMSecsSinceEpoch()
        
        # Throttle rapid seeks
        if current_time - self.last_seek_time < self.seek_throttle_ms:
            # Store the most recent position but don't seek yet
            self.pending_seek = position
            return
        
        # Perform the actual seek
        self._perform_seek(position)
        self.last_seek_time = current_time
        
        QTimer.singleShot(500, self._force_audio_resync)
        
    def _perform_seek(self, position):
        """Actually perform the seek operation"""
        length = self.player.get_length()
        if length > 0:
            new_time = int((position / 1000) * length)
            
            # Pause briefly before seeking for cleaner audio
            was_playing = self.player.is_playing()
            if was_playing:
                self.player.pause()
            
            # Perform the seek
            self.player.set_time(new_time)
            
            # Resume playback if it was playing
            if was_playing:
                QTimer.singleShot(10, self.player.play)  # Small delay before resuming

    def update_time(self):
        """Update current time and progress slider"""
        # Handle pending seeks from throttling
        if self.pending_seek is not None and self.player.get_media():
            current_time = QDateTime.currentMSecsSinceEpoch()
            if current_time - self.last_seek_time >= self.seek_throttle_ms:
                self._perform_seek(self.pending_seek)
                self.last_seek_time = current_time
                self.pending_seek = None
        
        # Rest of your existing update_time code...
        if self.player.get_media():
            ms = self.player.get_time()
            length = self.player.get_length()
            
            if ms >= 0:
                # Update time label
                seconds = ms // 1000
                self.current_time_label.setText(f"{seconds // 60:02d}:{seconds % 60:02d}")
                
                # Update progress slider
                if length > 0:
                    progress = int((ms / length) * 1000)
                    if not self.progress_slider.isSliderDown():  # Only update if user isn't dragging
                        self.progress_slider.setValue(progress)
                
    def seek_relative(self, ms_offset):
        """Seek forward or backward by specified milliseconds"""
        if self.player.get_media():
            current_time = self.player.get_time()
            new_time = max(0, current_time + ms_offset)
            self.player.set_time(new_time)

    def _force_audio_resync(self):
        """Force audio resynchronization"""
        if not self.player or not self.player.is_playing():
            return
        
        current_time = self.player.get_time()
        current_volume = self.player.audio_get_volume()
        
        # Briefly mute and unmute to trigger resync
        self.player.audio_set_volume(0)
        QTimer.singleShot(50, lambda: self.player.audio_set_volume(current_volume))
        
        # Or briefly pause/resume
        # self.player.pause()
        # QTimer.singleShot(100, self.player.play)
            
    def set_volume(self, value):
        """Set audio volume"""
        self.player.audio_set_volume(value)
        self.statusBar().showMessage(f"Volume: {value}%", 1000)
        
    def add_bookmark(self):
        """Add bookmark at current position"""
        if not self.current_file:
            QMessageBox.warning(self, "No File", "Please load an audio file first.")
            return
            
        if not self.player.get_media():
            QMessageBox.warning(self, "No Media", "No audio file is loaded.")
            return
            
        time_ms = self.player.get_time()
        if time_ms < 0:
            QMessageBox.warning(self, "Not Playing", "Audio is not playing.")
            return
        
        # Create a dialog for bookmark input
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Bookmark")
        dialog.setModal(True)
        dialog.setMinimumWidth(350)
        
        layout = QVBoxLayout(dialog)
        
        # Bookmark name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Name:")
        name_input = QLineEdit()
        name_input.setPlaceholderText(f"Bookmark at {time_ms // 1000}:{(time_ms % 1000):03d}")
        name_layout.addWidget(name_label)
        name_layout.addWidget(name_input, 1)
        layout.addLayout(name_layout)
        
        # Bookmark type selection
        type_layout = QHBoxLayout()
        type_label = QLabel("Type:")
        type_combo = QComboBox()
        type_combo.addItems(["Regular", "Start", "End"])
        type_combo.setCurrentText("Regular")
        type_layout.addWidget(type_label)
        type_layout.addWidget(type_combo)
        layout.addLayout(type_layout)
        
        # Time display
        time_display = QLabel(f"Time: {time_ms // 1000}:{(time_ms % 1000):03d} ms")
        time_display.setAlignment(Qt.AlignCenter)
        time_display.setStyleSheet("font-weight: bold;")
        layout.addWidget(time_display)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # Connect buttons
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        
        # Set focus to name input
        name_input.setFocus()
        
        # Show dialog and get result
        if dialog.exec() != QDialog.Accepted:
            return  # User canceled
            
        name = name_input.text().strip()
        if not name:
            name = f"Bookmark at {time_ms // 1000}:{time_ms % 1000:03d}"
        
        bookmark_type = type_combo.currentText()
            
        bookmark = {
            "file": self.current_file,
            "filename": os.path.basename(self.current_file),
            "time_ms": time_ms,
            "name": name,
            "type": bookmark_type,
            "timestamp": QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        }
        
        # Load existing bookmarks
        bookmarks = self.load_all_bookmarks()
        bookmarks.append(bookmark)
        
        # Save back to file
        try:
            with open(self.bookmarks_file, "w") as f:
                json.dump(bookmarks, f, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save bookmark:\n{str(e)}")
            return
            
        # Refresh display
        self.load_bookmarks()
        self.statusBar().showMessage(f"Bookmark '{name}' ({bookmark_type}) added", 3000)
    
    def update_bookmark_buttons_state(self):
        """Enable/disable bookmark buttons based on selection"""
        selected_items = self.bookmarks_list.selectedItems()
        has_selection = bool(selected_items)
        
        if has_selection:
            item = selected_items[0]
            bookmark = item.data(Qt.UserRole)
            # Enable only if it's a real bookmark (not a header)
            self.edit_bookmark_btn.setEnabled(bookmark is not None)
            self.delete_bookmark_btn.setEnabled(bookmark is not None)
        else:
            self.edit_bookmark_btn.setEnabled(False)
            self.delete_bookmark_btn.setEnabled(False)
    
    def load_all_bookmarks(self):
        """Load all bookmarks from file"""
        try:
            if os.path.exists(self.bookmarks_file):
                with open(self.bookmarks_file, "r") as f:
                    bookmarks = json.load(f)
                    # Ensure all bookmarks have a type field (for backward compatibility)
                    for bookmark in bookmarks:
                        if "type" not in bookmark:
                            bookmark["type"] = "Regular"
                    return bookmarks
        except Exception as e:
            print(f"Error loading bookmarks: {e}")
        return []
        
    def load_bookmarks(self):
        """Load and display bookmarks in the list widget"""
        self.bookmarks_list.clear()
        bookmarks = self.load_all_bookmarks()
        
        # Sort bookmarks by file, then by time
        bookmarks.sort(key=lambda x: (x["filename"], x["time_ms"]))
        
        # Group bookmarks by file
        current_file = None
        for i, bookmark in enumerate(bookmarks):
            time_sec = bookmark["time_ms"] // 1000
            time_str = f"{time_sec // 60:02d}:{time_sec % 60:02d}"
            bookmark_type = bookmark.get("type", "Regular")
            
            # Add file header if it's a new file
            if bookmark["filename"] != current_file:
                current_file = bookmark["filename"]
                header_item = QListWidgetItem(f"📁 {current_file}")
                header_item.setBackground(QColor(70, 70, 70))
                header_item.setFlags(header_item.flags() & ~Qt.ItemIsSelectable)
                self.bookmarks_list.addItem(header_item)
            
            # Create icon based on type
            if bookmark_type == "Start":
                icon_text = "▶️"
            elif bookmark_type == "End":
                icon_text = "⏹️"
            else:
                icon_text = "🔖"
            
            display_text = f"  {icon_text} {bookmark['name']} - {time_str} [{bookmark_type}]"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, bookmark)  # Store full bookmark data
            
            # Color code based on type
            if bookmark_type == "Start":
                item.setForeground(QColor(110, 240, 132))  # Green for start
            elif bookmark_type == "End":
                item.setForeground(QColor(232, 117, 104))  # Red for end
                
            self.bookmarks_list.addItem(item)
            
    def play_from_bookmark(self, item):
        """Play audio from selected bookmark position"""
        if item and self.current_file:
            bookmark = item.data(Qt.UserRole)
            
            # Skip if it's a header item (no UserRole data)
            if not bookmark:
                return
            
            # Check if bookmark is for current file
            if bookmark["file"] != self.current_file:
                reply = QMessageBox.question(
                    self,
                    "Different File",
                    f"This bookmark is for '{bookmark['filename']}'.\n"
                    f"Load this file instead?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    self.load_audio_file(bookmark["file"])
            
            # Seek to bookmark position
            self.player.set_time(bookmark["time_ms"])
            self.player.play()
            self.play_pause_btn.setText("⏸ Pause")  # Update button to Pause
            self.statusBar().showMessage(f"Playing from bookmark: {bookmark['name']} ({bookmark.get('type', 'Regular')})", 3000)
            
    def delete_selected_bookmark(self):
        """Delete the selected bookmark"""
        selected_items = self.bookmarks_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a bookmark to delete.")
            return
            
        item = selected_items[0]
        bookmark = item.data(Qt.UserRole)
        
        # Skip if it's a header item
        if not bookmark:
            return
        
        reply = QMessageBox.question(
            self,
            "Delete Bookmark",
            f"Delete bookmark '{bookmark['name']}' ({bookmark.get('type', 'Regular')})?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Load all bookmarks
            bookmarks = self.load_all_bookmarks()
            
            # Find and remove the bookmark
            for i, b in enumerate(bookmarks):
                if (b["file"] == bookmark["file"] and 
                    b["time_ms"] == bookmark["time_ms"] and 
                    b["name"] == bookmark["name"]):
                    del bookmarks[i]
                    break
                    
            # Save updated list
            try:
                with open(self.bookmarks_file, "w") as f:
                    json.dump(bookmarks, f, indent=2)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete bookmark:\n{str(e)}")
                return
                
            # Refresh display
            self.load_bookmarks()
            self.statusBar().showMessage("Bookmark deleted", 3000)
            
    def clear_bookmarks(self):
        """Clear all bookmarks"""
        reply = QMessageBox.question(
            self,
            "Clear Bookmarks",
            "Are you sure you want to clear ALL bookmarks?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(self.bookmarks_file):
                    os.remove(self.bookmarks_file)
                self.bookmarks_list.clear()
                self.statusBar().showMessage("All bookmarks cleared", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear bookmarks:\n{str(e)}")
                
    def edit_selected_bookmark(self):
        """Edit the selected bookmark"""
        selected_items = self.bookmarks_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a bookmark to edit.")
            return
            
        item = selected_items[0]
        bookmark = item.data(Qt.UserRole)
        
        # Skip if it's a header item
        if not bookmark:
            QMessageBox.warning(self, "Invalid Selection", "Please select a valid bookmark to edit.")
            return
        
        # Create edit dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Bookmark")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # Bookmark information display
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel(f"File: {bookmark['filename']}"))
        info_layout.addWidget(QLabel(f"Original Time: {bookmark['time_ms'] // 1000}:{(bookmark['time_ms'] % 1000):03d} ms"))
        layout.addLayout(info_layout)
        
        layout.addSpacing(10)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        layout.addSpacing(10)
        
        # Bookmark name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Name:")
        name_input = QLineEdit()
        name_input.setText(bookmark['name'])
        name_layout.addWidget(name_label)
        name_layout.addWidget(name_input, 1)
        layout.addLayout(name_layout)
        
        # Bookmark type selection
        type_layout = QHBoxLayout()
        type_label = QLabel("Type:")
        type_combo = QComboBox()
        type_combo.addItems(["Regular", "Start", "End"])
        type_combo.setCurrentText(bookmark.get('type', 'Regular'))
        type_layout.addWidget(type_label)
        type_layout.addWidget(type_combo)
        layout.addLayout(type_layout)
        
        # Time adjustment
        time_layout = QVBoxLayout()
        time_label = QLabel("Adjust Time (seconds):")
        time_layout.addWidget(time_label)
        
        time_adjust_layout = QHBoxLayout()
        
        # Current time display
        current_time_label = QLabel(f"Current: {bookmark['time_ms'] // 1000}:{(bookmark['time_ms'] % 1000):03d}")
        current_time_label.setAlignment(Qt.AlignCenter)
        current_time_label.setStyleSheet("font-weight: bold;")
        
        # Time adjustment controls
        time_spinbox = QSpinBox()
        time_spinbox.setRange(-bookmark['time_ms'] // 1000, 3600)  # Can go back to 0, forward up to 1 hour
        time_spinbox.setValue(0)
        time_spinbox.setSuffix(" seconds")
        
        # Use current player time button (only if same file is loaded)
        use_current_time_btn = QPushButton("Use Current Time")
        use_current_time_btn.setEnabled(self.current_file == bookmark['file'])
        
        def update_time_display():
            new_time_ms = bookmark['time_ms'] + (time_spinbox.value() * 1000)
            new_time_ms = max(0, new_time_ms)  # Don't allow negative time
            current_time_label.setText(f"New: {new_time_ms // 1000}:{(new_time_ms % 1000):03d}")
        
        def use_current_time():
            if self.player.get_media():
                current_ms = self.player.get_time()
                if current_ms >= 0:
                    time_spinbox.setValue((current_ms - bookmark['time_ms']) // 1000)
                    update_time_display()
        
        time_spinbox.valueChanged.connect(update_time_display)
        use_current_time_btn.clicked.connect(use_current_time)
        
        time_adjust_layout.addWidget(current_time_label, 1)
        time_adjust_layout.addWidget(time_spinbox)
        time_adjust_layout.addWidget(use_current_time_btn)
        
        time_layout.addLayout(time_adjust_layout)
        layout.addLayout(time_layout)
        
        layout.addSpacing(20)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Save Changes")
        cancel_button = QPushButton("Cancel")
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # Connect buttons
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        
        # Set focus to name input
        name_input.setFocus()
        name_input.selectAll()
        
        # Initialize time display
        update_time_display()
        
        # Show dialog and get result
        if dialog.exec() != QDialog.Accepted:
            return  # User canceled
        
        # Get new values
        new_name = name_input.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Invalid Name", "Bookmark name cannot be empty.")
            return
        
        new_type = type_combo.currentText()
        time_adjustment_seconds = time_spinbox.value()
        new_time_ms = bookmark['time_ms'] + (time_adjustment_seconds * 1000)
        new_time_ms = max(0, new_time_ms)  # Ensure non-negative
        
        # Load all bookmarks
        bookmarks = self.load_all_bookmarks()
        
        # Find the bookmark to edit
        bookmark_index = -1
        for i, b in enumerate(bookmarks):
            if (b["file"] == bookmark["file"] and 
                b["time_ms"] == bookmark["time_ms"] and 
                b["name"] == bookmark["name"]):
                bookmark_index = i
                break
        
        if bookmark_index == -1:
            QMessageBox.warning(self, "Bookmark Not Found", "The bookmark could not be found in the database.")
            return
        
        # Update the bookmark
        bookmarks[bookmark_index]["name"] = new_name
        bookmarks[bookmark_index]["type"] = new_type
        bookmarks[bookmark_index]["time_ms"] = new_time_ms
        bookmarks[bookmark_index]["timestamp"] = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        
        # Save back to file
        try:
            with open(self.bookmarks_file, "w") as f:
                json.dump(bookmarks, f, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save bookmark changes:\n{str(e)}")
            return
        
        # Refresh display
        self.load_bookmarks()
        
        # Reselect the edited bookmark
        for i in range(self.bookmarks_list.count()):
            item = self.bookmarks_list.item(i)
            if item:
                bm = item.data(Qt.UserRole)
                if bm and (bm["file"] == bookmark["file"] and 
                          bm["name"] == new_name and 
                          bm["time_ms"] == new_time_ms):
                    self.bookmarks_list.setCurrentItem(item)
                    break
        
        self.statusBar().showMessage(f"Bookmark updated to '{new_name}' ({new_type})", 3000)
                
    def reset_player(self):
        """Reset player to initial state"""
        self.current_file = ""
        self.file_label.setText("No file selected")
        self.play_pause_btn.setEnabled(False)
        self.play_pause_btn.setText("▶ Play")  # Reset to Play text
        self.stop_btn.setEnabled(False)
        self.bookmark_btn.setEnabled(False)
        self.progress_slider.setEnabled(False)
        self.current_time_label.setText("00:00")
        self.total_time_label.setText("00:00")
        self.progress_slider.setValue(0)
        
    def closeEvent(self, event):
        """Handle window close event"""
        self.player.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show main window
    player = EnhancedAudioPlayer()
    player.setWindowTitle("Enhanced Audio Player with Bookmarks")
    player.setGeometry(100, 100, 800, 600)
    player.show()
    
    sys.exit(app.exec())