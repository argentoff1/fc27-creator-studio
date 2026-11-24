STYLESHEET = """
QMainWindow, QWidget {
    background-color: #15171c;
    color: #e8eaf0;
    font-family: "Segoe UI";
    font-size: 10pt;
}

QFrame#Sidebar {
    background-color: #1d2027;
    border: none;
}

QLabel#Logo {
    font-size: 18pt;
    font-weight: bold;
    color: #ffffff;
}

QLabel#Subtitle {
    color: #9299a8;
    font-size: 9pt;
}

QLabel {
    background-color: transparent;
    border: none;
    padding-left: 3px;
}

QLabel#PageTitle {
    font-size: 22pt;
    font-weight: bold;
    color: #ffffff;
}

QPushButton {
    background-color: #292e38;
    color: #e8eaf0;
    border: none;
    border-radius: 7px;
    padding: 11px 13px;
    text-align: left;
}

QPushButton:hover {
    background-color: #383f4d;
}

QPushButton#ActiveButton {
    background-color: #354b70;
    color: white;
}

QPushButton#ActionButton {
    background-color: #3569c8;
    color: white;
    font-weight: bold;
    text-align: center;
    padding: 14px;
}

QPushButton#ActionButton:hover {
    background-color: #477fe0;
}

QPushButton#SendToEditorButton {
    background-color: #292e38;
    color: #858c99;
    font-weight: bold;
}

QPushButton#SendToEditorButton:disabled {
    background-color: #292e38;
    color: #858c99;
}

QPushButton#SendToEditorButton:enabled {
    background-color: #3569c8;
    color: white;
    font-weight: bold;
}

QPushButton#SendToEditorButton:enabled:hover {
    background-color: #477fe0;
}

QPushButton#TrimButton {
    background-color: #292e38;
    color: #e8eaf0;
}

QPushButton#TrimButtonSelectedStart {
    background-color: #3569c8;
    color: white;
    font-weight: bold;
}

QPushButton#TrimButtonSelectedEnd {
    background-color: #238653;
    color: white;
    font-weight: bold;
}

QPushButton#TrimButton:hover {
    background-color: #383f4d;
}

QPushButton#TrimButtonSelectedStart:hover {
    background-color: #477fe0;
}

QPushButton#TrimButtonSelectedEnd:hover {
    background-color: #2da568;
}

QFrame#ContentCard {
    background-color: #20242d;
    border: 1px solid #303642;
    border-radius: 10px;
}

QFrame#ContentCard:hover {
    background-color: #292f3a;
    border: 1px solid #4b6388;
}

QLabel#CardTitle {
    font-size: 12pt;
    font-weight: bold;
}

QLabel#CardDescription {
    color: #a3aab8;
}

QLabel#Status {
    color: #55c98a;
}

QTableWidget {
    background-color: #1d2027;
    alternate-background-color: #252a34;
    color: #e8eaf0;
    gridline-color: #303642;
    border: 1px solid #303642;
    selection-background-color: #354b70;
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 6px;
}

QHeaderView::section {
    background-color: #292e38;
    color: #ffffff;
    padding: 9px;
    border: none;
    border-right: 1px solid #3a414e;
    border-bottom: 1px solid #3a414e;
    font-weight: bold;
}

QTableWidget QTableCornerButton::section {
    background-color: #292e38;
    border: none;
}

QScrollBar:vertical {
    background-color: #1d2027;
    width: 12px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #515b6c;
    min-height: 30px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #71809a;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}
"""