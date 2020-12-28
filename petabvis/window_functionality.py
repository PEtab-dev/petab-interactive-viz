# Import after PySide2 to ensure usage of correct Qt library
import os
import sys
from pathlib import Path

import pandas as pd
from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtCore import (QAbstractTableModel, QModelIndex, Qt,
                            QSortFilterProxyModel)
from PySide2.QtGui import QColor
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import (QAction, QVBoxLayout, QHeaderView,
                               QSizePolicy, QTableView, QWidget, QFileDialog)

import petab
import petab.C as ptc
from petab import core
from petab.visualize.helper_functions import check_ex_exp_columns


class CustomTableModel(QAbstractTableModel):
    """PEtab data table model."""

    def __init__(self, data=None):
        QAbstractTableModel.__init__(self)
        self.load_data(data)
        self.df = data

    def load_data(self, data):
        for x in data:
            setattr(self, x, data[x])
        self.column_count = data.shape[1]
        self.row_count = data.shape[0]

    def rowCount(self, parent=QModelIndex()):
        return self.row_count

    def columnCount(self, parent=QModelIndex()):
        return self.column_count

    def headerData(self, section, orientation, role=None):
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            return self.df.columns[section]
        else:
            return "{}".format(section)

    def data(self, index, role=Qt.DisplayRole):
        column = index.column()
        row = index.row()

        if role == Qt.DisplayRole:
            return str(self.df.iloc[row, column])

        elif role == Qt.BackgroundRole:
            return QColor(Qt.white)

        elif role == Qt.TextAlignmentRole:
            return Qt.AlignRight

        return None


class TableWidget(QWidget):
    """Main widget"""

    def __init__(self, data: pd.DataFrame):
        QWidget.__init__(self)

        # Getting the Model
        self.model = CustomTableModel(data)

        # Creating a QTableView
        self.table_view = QTableView()
        self.filter_proxy = QSortFilterProxyModel()
        self.filter_proxy.setSourceModel(self.model)
        self.table_view.setModel(self.filter_proxy)
        self.table_view.setSortingEnabled(True)

        # QTableView Headers
        self.horizontal_header = self.table_view.horizontalHeader()
        self.horizontal_header.setSortIndicator(-1, Qt.DescendingOrder)
        self.vertical_header = self.table_view.verticalHeader()
        self.horizontal_header.setSectionResizeMode(QHeaderView.ResizeToContents)
        self.vertical_header.setSectionResizeMode(QHeaderView.ResizeToContents)
        self.horizontal_header.setStretchLastSection(True)

        # QWidget Layout
        self.main_layout = QVBoxLayout()
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        size.setHorizontalStretch(1)
        self.table_view.setSizePolicy(size)
        self.main_layout.addWidget(self.table_view)

        self.setLayout(self.main_layout)


def pop_up_table_view(window: QtWidgets.QMainWindow, df: pd.DataFrame):
    """
    Create a popup window that displays the dataframe

    Arguments:
        window: The mainwindow to which the TableWidget gets added
        df: The dataframe to display
    """
    window.table_window = TableWidget(df)
    window.table_window.setGeometry(QtCore.QRect(100, 100, 800, 400))
    window.table_window.show()




def table_tree_view(window: QtWidgets.QMainWindow, folder_path):
    """
    Create a treeview of the yaml file

    Arguments:
        window: The Mainwindow to which the treeview is added
        folder_path: The path to the folder the yaml file is in
    """
    model = QtGui.QStandardItemModel()
    tree_view = window.tree_view
    root_node = model.invisibleRootItem()

    for key in window.yaml_dict:
        branch = QtGui.QStandardItem(key)
        for filename in window.yaml_dict[key]:
            file = QtGui.QStandardItem(filename)
            df = None
            if key == ptc.MEASUREMENT_FILES:
                df = petab.get_measurement_df(folder_path + "/" + filename)
            if key == ptc.VISUALIZATION_FILES:
                df = petab.get_visualization_df(folder_path + "/" + filename)
            if key == ptc.CONDITION_FILES:
                df = petab.get_condition_df(folder_path + "/" + filename)
            if key == ptc.OBSERVABLE_FILES:
                df = petab.get_observable_df(folder_path + "/" + filename)
            file.setData(df, role=Qt.UserRole + 1)
            branch.appendRow(file)
        root_node.appendRow(branch)

    if window.simulation_df is not None:
        branch = QtGui.QStandardItem("simulation_files")
        simulation_file = QtGui.QStandardItem("simulation_file")
        simulation_file.setData(window.simulation_df, role=Qt.UserRole + 1)
        branch.appendRow(simulation_file)
        root_node.appendRow(branch)

    tree_view.setModel(model)
    tree_view.clicked.connect(lambda i: exchange_dataframe_on_click(i, model, window))
    tree_view.doubleClicked.connect(lambda i: display_table_on_doubleclick(i, model, window))


def exchange_dataframe_on_click(index: QtCore.QModelIndex, model: QtGui.QStandardItemModel, window: QtWidgets.QMainWindow):
    """
    Changes the currently plotted dataframe with the one
    that gets clicked on and replot the data
    e.g. switch the measurement or visualization df

    Arguments:
        index: index of the clicked dataframe
        model: model containing the data
        window: Mainwindow whose attributes get updated
    """
    name = model.data(index, QtCore.Qt.DisplayRole)
    df = model.data(index, role=Qt.UserRole + 1)
    parent = index.parent()
    parent_name = model.data(parent, QtCore.Qt.DisplayRole)
    if parent_name == ptc.MEASUREMENT_FILES:
        window.exp_data = df
    if parent_name == ptc.VISUALIZATION_FILES:
        window.visualization_df = df
    if parent_name == ptc.CONDITION_FILES:
        window.condition_df = df
    window.add_plots()


def display_table_on_doubleclick(index: QtCore.QModelIndex, model: QtGui.QStandardItemModel, window: QtWidgets.QMainWindow):
    """
    Display the dataframe in a new window upon double-click

    Arguments:
        index: index of the clicked dataframe
        model: model containing the data
        window: Mainwindow whose attributes get updated
    """
    name = model.data(index, QtCore.Qt.DisplayRole)
    df = model.data(index, role=Qt.UserRole + 1)
    if df is not None:
        pop_up_table_view(window, df)


def add_file_selector(window: QtWidgets.QMainWindow):
    """
    Adds a file selector button to the main window
    Arguments:
        window: Mainwindow
    """
    open_yaml_file = QAction(QIcon('open.png'), 'Open YAML file...', window)
    open_yaml_file.triggered.connect(lambda x: show_yaml_dialog(x, window))
    open_simulation_file = QAction(QIcon('open.png'), 'Open simulation file...', window)
    open_simulation_file.triggered.connect(lambda x: show_simulation_dialog(x, window))
    quit = QAction("Quit", window)
    quit.triggered.connect(sys.exit)

    menubar = window.menuBar()
    fileMenu = menubar.addMenu('&Select File')
    fileMenu.addAction(open_yaml_file)
    fileMenu.addAction(open_simulation_file)
    fileMenu.addAction(quit)


def show_yaml_dialog(self, window: QtWidgets.QMainWindow):
    """
    Display a file selector window when clicking on the select YAML file menu
    item, then display the new plots described by the YAML file.

    Arguments:
        window: Mainwindow
    """
    home_dir = str(Path.home())
    # start file selector on the last selected directory
    settings = QtCore.QSettings("petab", "petabvis")
    if settings.value("last_dir") is not None:
        home_dir = settings.value("last_dir")
    file_name = QFileDialog.getOpenFileName(window, 'Open file', home_dir)[0]
    if file_name != "":  # if a file was selected
        # save the directory for the next use
        last_dir = os.path.dirname(file_name)
        settings.setValue("last_dir", last_dir)

        window.warn_msg.setText("")

        # select the first df in the dict for measurements, etc.
        yaml_dict = petab.load_yaml(file_name)["problems"][0]
        window.yaml_dict = yaml_dict
        window.exp_data = petab.get_measurement_df(last_dir + "/" + yaml_dict[ptc.MEASUREMENT_FILES][0])
        window.condition_df = petab.get_condition_df(last_dir + "/" + yaml_dict[ptc.CONDITION_FILES][0])
        window.simulation_df = None
        if ptc.VISUALIZATION_FILES in yaml_dict:
            window.visualization_df = petab.get_visualization_df(last_dir + "/" + yaml_dict[ptc.VISUALIZATION_FILES][0])
        else:
            window.visualization_df = None
            window.add_warning("The YAML file contains no visualization file (default plotted)")
        window.add_plots()


        window.listWidget = table_tree_view(window, last_dir)


def show_simulation_dialog(self, window: QtWidgets.QMainWindow):
    """
    Displays a file selector window when clicking on the select simulation file button
    Then adds the simulation lines to the plots

    Arguments:
        window: Mainwindow
    """
    home_dir = str(Path.home())
    settings = QtCore.QSettings("petab", "petabvis")
    if settings.value("last_dir") is not None:
        home_dir = settings.value("last_dir")
    file_name = QFileDialog.getOpenFileName(window, 'Open simulation file', home_dir)[0]
    if file_name != "":  # if a file was selected
        if window.exp_data is None:
            window.add_warning("Please open a YAML file first.")
        else:
            window.warn_msg.setText("")
            sim_data = core.get_simulation_df(file_name)
            # check columns, and add non-mandatory default columns
            sim_data, _, _ = check_ex_exp_columns(sim_data, None, None, None, None, None,
                                                  window.condition_df, sim=True)
            # delete the replicateId column if it gets added to the simulation table
            # but is not in exp_data because it causes problems when splitting the replicates
            if ptc.REPLICATE_ID not in window.exp_data.columns and ptc.REPLICATE_ID in sim_data.columns:
                sim_data.drop(ptc.REPLICATE_ID, axis=1, inplace=True)
            window.simulation_df = sim_data
            window.add_plots()

            # insert correlation plot at position 1
            window.wid.insertWidget(1, window.plot2_widget)
            window.listWidget = table_tree_view(window, os.path.dirname(file_name))

        # save the directory for the next use
        last_dir = os.path.dirname(file_name)
        settings.setValue("last_dir", last_dir)