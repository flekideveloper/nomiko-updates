"""NOMIKO local theme presets and portable, validated theme files."""
from __future__ import annotations

from pathlib import Path
import json
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QSlider, QVBoxLayout,
)

from .theme_data import THEME_KEYS, THEME_PRESETS, sanitize_theme


class ThemeStudioDialog(QDialog):
    def __init__(self, browser):
        super().__init__(browser)
        self.browser=browser
        self.setWindowTitle('NOMIKO · Theme Studio 2.0')
        self.resize(465,370)
        root=QVBoxLayout(self)
        root.addWidget(QLabel('Every change is applied immediately. Themes are local files, no server required.'))
        form=QFormLayout()
        root.addLayout(form)
        self.preset=QComboBox()
        self.preset.addItems(THEME_PRESETS)
        form.addRow('Preset:',self.preset)
        self.preset.currentTextChanged.connect(self.apply_preset)
        self.accent=QPushButton('Pick custom accent…')
        self.accent.clicked.connect(self.choose_color)
        form.addRow('Accent:',self.accent)
        self.font=QSlider(Qt.Orientation.Horizontal)
        self.font.setRange(10,16)
        self.font.setValue(int(browser.store.settings.get('theme_font_size',12)))
        self.font.valueChanged.connect(lambda v:browser.update_preference(theme_font_size=v))
        form.addRow('Interface font size:',self.font)
        self.opacity=QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(0,65)
        self.opacity.setValue(browser.store.settings.get('interface_transparency',{}).get('toolbar',0))
        self.opacity.valueChanged.connect(self.set_toolbar_opacity)
        form.addRow('Toolbar blending:',self.opacity)
        row=QHBoxLayout()
        for title,cb in [('Export theme…',self.export),('Import theme…',self.load)]:
            b=QPushButton(title);b.clicked.connect(cb);row.addWidget(b)
        root.addLayout(row)
        root.addWidget(QLabel('Imported themes cannot execute code or install browser extensions.'))
        root.addStretch(1)

    def apply_preset(self, name):
        theme, accent = THEME_PRESETS[name]
        self.browser.update_preference(theme=theme, accent=accent)

    def choose_color(self):
        color=QColorDialog.getColor(QColor(self.browser.store.settings.get('accent','#9A82FF')),self)
        if color.isValid(): self.browser.update_preference(accent=color.name())

    def set_toolbar_opacity(self,value):
        values=dict(self.browser.store.settings.get('interface_transparency',{}))
        values['toolbar']=value
        self.browser.update_preference(interface_transparency=values)

    def export(self):
        filename,_=QFileDialog.getSaveFileName(self,'Export theme','nomiko-theme.json','NOMIKO Theme (*.json)')
        if filename:
            obj={key:self.browser.store.settings.get(key) for key in THEME_KEYS}
            try: Path(filename).write_text(json.dumps(obj,indent=2),encoding='utf-8')
            except OSError as err: QMessageBox.warning(self,'Export failed',str(err))

    def load(self):
        filename,_=QFileDialog.getOpenFileName(self,'Import theme','','NOMIKO Theme (*.json)')
        if not filename:return
        try:
            if Path(filename).stat().st_size>20_000:raise ValueError('Theme file must be smaller than 20 KB')
            data=json.loads(Path(filename).read_text(encoding='utf-8'))
            self.browser.update_preference(**sanitize_theme(data))
        except (OSError,ValueError,TypeError) as err:
            QMessageBox.warning(self,'Import failed',str(err))
