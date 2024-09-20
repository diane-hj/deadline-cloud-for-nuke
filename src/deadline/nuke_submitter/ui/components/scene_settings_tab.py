# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
UI widgets for the Scene Settings tab.
"""
import os
import nuke
from PySide2.QtCore import Qt  # type: ignore
from PySide2.QtWidgets import (  # type: ignore
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QRadioButton,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QSizePolicy,
    QSpacerItem,
    QWidget,
    QSpinBox,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
)
from typing import Optional

from ...assets import find_all_write_nodes
from ...data_classes import RenderSubmitterUISettings, StepSetting

STEP_NAME = "step_name"
FRAME = "frame"
WRITE_NODE = "write_node"


class SceneSettingsWidget(QWidget):
    """
    Widget containing all top level scene settings.
    """

    def __init__(self, initial_settings: RenderSubmitterUISettings, parent=None):
        super().__init__(parent=parent)

        self.developer_options = (
            os.environ.get("DEADLINE_ENABLE_DEVELOPER_OPTIONS", "").upper() == "TRUE"
        )

        self._build_ui()
        self.refresh_ui(initial_settings)

    def _build_ui(self):
        lyt = QGridLayout(self)

        lyt.addWidget(QLabel("Write Nodes"), 0, 0)
        self.submit_single_step_button = QRadioButton("Submit Single Step")
        self.write_node_box = QComboBox(self)
        self._rebuild_write_node_drop_down(self.write_node_box, include_all_write_nodes=True)
        lyt.addWidget(self.submit_single_step_button, 1, 0)
        lyt.addWidget(self.write_node_box, 1, 1, 1, -1)

        def add_step_input_row(first: Optional[bool] = False):
            box_layout = QHBoxLayout()
            step_name_box = QLineEdit(self)
            step_name_box.setObjectName(STEP_NAME)
            step_name_box.setPlaceholderText("Step Name")
            box_layout.addWidget(step_name_box)

            write_node_box = QComboBox(self)
            write_node_box.setObjectName(WRITE_NODE)
            self._rebuild_write_node_drop_down(write_node_box, include_all_write_nodes=False)
            box_layout.addWidget(write_node_box)

            frame_box = QLineEdit(self)
            frame_box.setObjectName(FRAME)
            frame_box.setPlaceholderText("Frame")
            box_layout.addWidget(frame_box)
            
            def remove_step_row():
                frame_box.deleteLater()
                write_node_box.deleteLater()
                step_name_box.deleteLater()
                remove_step_button.deleteLater()
                box_layout.deleteLater()
            if first:
                add_more_steps_button = QPushButton("+")
                add_more_steps_button.setFixedSize(15, 15)
                box_layout.addWidget(add_more_steps_button)
                add_more_steps_button.clicked.connect(add_step_input_row)
            else:
                remove_step_button = QPushButton("-")
                remove_step_button.setFixedSize(15, 15)
                remove_step_button.clicked.connect(remove_step_row)
                box_layout.addWidget(remove_step_button)

            self.multiple_steps_group_box.addLayout(box_layout)

        self.submit_multiple_steps_button = QRadioButton("Submit Multiple Steps")
        lyt.addWidget(self.submit_multiple_steps_button, 2, 0)
        self.multiple_steps_group_box = QVBoxLayout()
        lyt.addLayout(self.multiple_steps_group_box, 2, 1)
        add_step_input_row(first=True)

        self.submit_single_step_button.clicked.connect(self.control_multiple_steps_button)
        self.submit_multiple_steps_button.clicked.connect(self.control_simple_step_button)

        self.views_box = QComboBox(self)
        self._rebuild_views_drop_down()
        lyt.addWidget(QLabel("Views"), 3, 0)
        lyt.addWidget(self.views_box, 3, 1, 1, -1)

        self.frame_override_chck = QCheckBox("Override Frame Range", self)
        self.frame_override_txt = QLineEdit(self)
        lyt.addWidget(self.frame_override_chck, 4, 0)
        lyt.addWidget(self.frame_override_txt, 4, 1, 1, -1)
        self.frame_override_chck.stateChanged.connect(self.activate_frame_override_changed)

        self.proxy_mode_check = QCheckBox("Use Proxy Mode", self)
        lyt.addWidget(self.proxy_mode_check, 5, 0)

        self.timeout_checkbox = QCheckBox("Use Timeouts", self)
        self.timeout_checkbox.setChecked(True)
        self.timeout_checkbox.clicked.connect(self.activate_timeout_changed)
        self.timeout_checkbox.setToolTip(
            "Set a maximum duration for actions from this job. See AWS Deadline Cloud documentation to learn more"
        )
        lyt.addWidget(self.timeout_checkbox, 6, 0)
        self.timeouts_subtext = QLabel("Set a maximum duration for actions from this job")
        self.timeouts_subtext.setStyleSheet("font-style: italic")
        lyt.addWidget(self.timeouts_subtext, 6, 1, 1, -1)

        self.timeouts_box = QGroupBox()
        timeouts_lyt = QGridLayout(self.timeouts_box)
        lyt.addWidget(self.timeouts_box, 5, 0, 1, -1)

        self.gizmos_checkbox = QCheckBox("Include Gizmos In Job Bundle", self)
        lyt.addWidget(self.gizmos_checkbox, 6, 0)

        def create_timeout_row(label, tooltip, row):
            qlabel = QLabel(label)
            qlabel.setToolTip(tooltip)
            timeouts_lyt.addWidget(qlabel, row, 0)

            days_box = QSpinBox(self, minimum=0, maximum=365)
            days_box.setSuffix(" days")
            timeouts_lyt.addWidget(days_box, row, 1)

            hours_box = QSpinBox(self, minimum=0, maximum=23)
            hours_box.setSuffix(" hours")
            timeouts_lyt.addWidget(hours_box, row, 2)

            minutes_box = QSpinBox(self, minimum=0, maximum=59)
            minutes_box.setSuffix(" minutes")
            timeouts_lyt.addWidget(minutes_box, row, 3)

            return qlabel, days_box, hours_box, minutes_box

        def hookup_zero_callback(timeout_boxes: tuple[QLabel, QSpinBox, QSpinBox, QSpinBox]):
            def indicate_is_valid_callback(value: int):
                self.indicate_if_valid(timeout_boxes)

            for timeout_box in timeout_boxes[1:]:
                timeout_box.valueChanged.connect(indicate_is_valid_callback)

        self.on_run_timeouts = create_timeout_row(
            label="Render Task Timeout",
            tooltip="Maximum duration of each action which performs a render. Default is 6 days.",
            row=0,
        )
        hookup_zero_callback(self.on_run_timeouts)

        self.on_enter_timeouts = create_timeout_row(
            label="Setup Timeout",
            tooltip="Maximum duration of each action which sets up the job for rendering, such as scene load. Default is 1 day.",
            row=1,
        )
        hookup_zero_callback(self.on_enter_timeouts)

        self.on_exit_timeouts = create_timeout_row(
            label="Teardown Timeout",
            tooltip="Maximum duration of action which tears down the setup required for rendering. Default is 1 hour.",
            row=2,
        )
        hookup_zero_callback(self.on_exit_timeouts)

        if self.developer_options:
            self.include_adaptor_wheels = QCheckBox(
                "Developer Option: Include Adaptor Wheels", self
            )
            lyt.addWidget(self.include_adaptor_wheels, 8, 0, 1, 2)

        lyt.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding), 7, 0)

    def indicate_if_valid(self, timeout_boxes: tuple[QLabel, QSpinBox, QSpinBox, QSpinBox]):
        if (
            self._calculate_timeout_seconds(timeout_boxes) == 0
            and self.timeout_checkbox.isChecked()
        ):
            timeout_boxes[0].setStyleSheet("color: red")
        else:
            timeout_boxes[0].setStyleSheet("")

        # If the spin box has a value of 1, we should not make the suffix plural.
        for box in timeout_boxes[1:4]:
            if box.value() == 1:
                box.setSuffix(box.suffix().strip("s"))
            elif not box.suffix().endswith("s"):
                box.setSuffix(box.suffix() + "s")

    def activate_timeout_changed(self, _=None, warn=True):
        state = self.timeout_checkbox.checkState()
        if state == Qt.Unchecked and warn:
            result = QMessageBox.warning(
                self,
                "Warning",
                "Removing timeouts in your submission can result in a task that runs indefinitely. Are you sure you want to remove timeouts?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if result == QMessageBox.No:
                self.timeout_checkbox.setChecked(True)
        for timeout_boxes in (self.on_run_timeouts, self.on_enter_timeouts, self.on_exit_timeouts):
            for timeout_box in timeout_boxes:
                timeout_box.setEnabled(state == Qt.Checked)
            self.indicate_if_valid(timeout_boxes)

    def _calculate_timeout_seconds(
        self, timeout_boxes: tuple[QLabel, QSpinBox, QSpinBox, QSpinBox]
    ):
        return (
            timeout_boxes[1].value() * 86400
            + timeout_boxes[2].value() * 3600
            + timeout_boxes[3].value() * 60
        )

    def _rebuild_write_node_drop_down(self, combo_box, include_all_write_nodes) -> None:
        combo_box.clear()
        if include_all_write_nodes:
            combo_box.addItem("All Write Nodes", None)
        for write_node in sorted(
            find_all_write_nodes(), key=lambda write_node: write_node.fullName()
        ):
            # Set data value as fullName since this is the value we want to store in the settings
            combo_box.addItem(write_node.fullName(), write_node.fullName())

    def _rebuild_views_drop_down(self) -> None:
        self.views_box.clear()
        self.views_box.addItem("All Views", "")
        for view in sorted(nuke.views()):
            self.views_box.addItem(view, view)

    @property
    def on_run_timeout_seconds(self):
        return self._calculate_timeout_seconds(self.on_run_timeouts)

    @property
    def on_enter_timeout_seconds(self):
        return self._calculate_timeout_seconds(self.on_enter_timeouts)

    @property
    def on_exit_timeout_seconds(self):
        return self._calculate_timeout_seconds(self.on_exit_timeouts)

    def refresh_ui(self, settings: RenderSubmitterUISettings):
        self.frame_override_chck.setChecked(settings.override_frame_range)
        self.frame_override_txt.setEnabled(settings.override_frame_range)
        self.frame_override_txt.setText(settings.frame_list)

        # self._rebuild_write_node_drop_down()
        # index = self.write_node_box.findData(settings.write_node_selection)
        # if index >= 0:
        #     self.write_node_box.setCurrentIndex(index)
        # else:
        #     self.write_node_box.setCurrentIndex(0)

        self._rebuild_views_drop_down()
        index = self.views_box.findData(settings.view_selection)
        if index >= 0:
            self.views_box.setCurrentIndex(index)
        else:
            self.views_box.setCurrentIndex(0)

        self.proxy_mode_check.setChecked(settings.is_proxy_mode)

        self.timeout_checkbox.setChecked(settings.timeouts_enabled)

        def _set_timeout(
            timeout_boxes: tuple[QLabel, QSpinBox, QSpinBox, QSpinBox], timeout_seconds: int
        ):
            days = timeout_seconds // 86400
            hours = (timeout_seconds % 86400) // 3600
            minutes = (timeout_seconds % 3600) // 60
            timeout_boxes[1].setValue(days)
            timeout_boxes[2].setValue(hours)
            timeout_boxes[3].setValue(minutes)

        _set_timeout(self.on_run_timeouts, settings.on_run_timeout_seconds)
        _set_timeout(self.on_enter_timeouts, settings.on_enter_timeout_seconds)
        _set_timeout(self.on_exit_timeouts, settings.on_exit_timeout_seconds)

        if self.developer_options:
            self.include_adaptor_wheels.setChecked(settings.include_adaptor_wheels)

        self.activate_timeout_changed(warn=False)  # don't warn when loading from sticky settings

    def update_settings(self, settings: RenderSubmitterUISettings):
        """
        Update a scene settings object with the latest values.
        """
        settings.override_frame_range = self.frame_override_chck.isChecked()
        settings.frame_list = self.frame_override_txt.text()

        if self.submit_single_step_button.isChecked():
            settings.write_node_selection = self.write_node_box.currentData()
        elif self.submit_multiple_steps_button.isChecked():
            previous_step_name = None
            for i in range(self.multiple_steps_group_box.count()):
                child_widget = self.multiple_steps_group_box.itemAt(i)

                step_name = child_widget.itemAt(0).widget().text()
                write_node = child_widget.itemAt(1).widget().currentData()
                frame_range = child_widget.itemAt(2).widget().text()
                step = StepSetting(
                    step_name=step_name, write_node=write_node, frame_range=frame_range, depends_on=previous_step_name
                )
                settings.multiple_steps_selection_list.append(step)
                previous_step_name = step_name
        else:
            # One of them should be chosen
            nuke.tprint("pick xomething!")
        settings.view_selection = self.views_box.currentData()
        settings.is_proxy_mode = self.proxy_mode_check.isChecked()

        settings.timeouts_enabled = self.timeout_checkbox.isChecked()
        settings.on_run_timeout_seconds = self.on_run_timeout_seconds
        settings.on_enter_timeout_seconds = self.on_enter_timeout_seconds
        settings.on_exit_timeout_seconds = self.on_exit_timeout_seconds

        settings.include_gizmos_in_job_bundle = self.gizmos_checkbox.isChecked()

        if self.developer_options:
            settings.include_adaptor_wheels = self.include_adaptor_wheels.isChecked()
        else:
            settings.include_adaptor_wheels = False

    def activate_frame_override_changed(self, state: int):
        """
        Set the activated/deactivated status of the Frame override text box
        """
        self.frame_override_txt.setEnabled(state == Qt.Checked)

    def control_multiple_steps_button(self, state: int):
        self.multiple_steps_group_box.setEnabled(False)
        self.write_node_box.setEnabled(True)


    def control_simple_step_button(self, state: int):
        self.multiple_steps_group_box.setEnabled(True)
        self.write_node_box.setEnabled(False)
