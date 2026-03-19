from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QTreeWidget, 
                            QTreeWidgetItem, QSplitter, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QTextEdit, QLineEdit, QFormLayout)
from PyQt6.QtCore import Qt
import sys
from dataclasses import dataclass
from typing import Optional, Dict
import json

@dataclass
class AgentConfig:
    name: str
    role: str
    context: str
    avatar_path: Optional[str] = None
    
    def to_dict(self):
        return {
            'name': self.name,
            'role': self.role,
            'context': self.context,
            'avatar_path': self.avatar_path
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)

class AgentManagerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Agent Manager")
        self.setGeometry(100, 100, 1200, 800)
        
        # Hauptcontainer
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Splitter für Tree und Detail-Ansicht
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Linke Seite - Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("AI Agents")
        self.tree.itemClicked.connect(self.on_item_selected)
        splitter.addWidget(self.tree)
        
        # Rechte Seite - Detail View
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        splitter.addWidget(right_widget)
        
        # Form Layout für Details
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        right_layout.addWidget(form_widget)
        
        # Eingabefelder
        self.name_input = QLineEdit()
        self.role_input = QLineEdit()
        self.context_input = QTextEdit()
        self.avatar_path_input = QLineEdit()
        
        form_layout.addRow("Name:", self.name_input)
        form_layout.addRow("Role:", self.role_input)
        form_layout.addRow("Context:", self.context_input)
        form_layout.addRow("Avatar Path:", self.avatar_path_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        right_layout.addLayout(button_layout)
        
        self.save_button = QPushButton("Save Agent")
        self.save_button.clicked.connect(self.save_agent)
        button_layout.addWidget(self.save_button)
        
        self.new_button = QPushButton("New Agent")
        self.new_button.clicked.connect(self.new_agent)
        button_layout.addWidget(self.new_button)
        
        self.delete_button = QPushButton("Delete Agent")
        self.delete_button.clicked.connect(self.delete_agent)
        button_layout.addWidget(self.delete_button)
        
        # Daten-Dictionary für Agenten
        self.agents: Dict[str, AgentConfig] = {}
        
        # Standard-Agenten laden
        self.load_default_agents()
        self.update_tree()
    
    def load_default_agents(self):
        # Project Manager als Beispiel-Agent
        pm_agent = AgentConfig(
            name="Project Manager",
            role="project_manager",
            context="""You are an experienced project manager in a software development team.
            Your task is to analyze requirements and coordinate the team."""
        )
        self.agents[pm_agent.name] = pm_agent
    
    def update_tree(self):
        self.tree.clear()
        for name, agent in self.agents.items():
            item = QTreeWidgetItem([name])
            self.tree.addTopLevelItem(item)
    
    def on_item_selected(self, item):
        agent = self.agents.get(item.text(0))
        if agent:
            self.name_input.setText(agent.name)
            self.role_input.setText(agent.role)
            self.context_input.setText(agent.context)
            self.avatar_path_input.setText(agent.avatar_path or "")
    
    def save_agent(self):
        name = self.name_input.text()
        if name:
            agent = AgentConfig(
                name=name,
                role=self.role_input.text(),
                context=self.context_input.toPlainText(),
                avatar_path=self.avatar_path_input.text() or None
            )
            self.agents[name] = agent
            self.update_tree()
            self.save_to_file()
    
    def new_agent(self):
        self.name_input.clear()
        self.role_input.clear()
        self.context_input.clear()
        self.avatar_path_input.clear()
    
    def delete_agent(self):
        current_item = self.tree.currentItem()
        if current_item:
            name = current_item.text(0)
            if name in self.agents:
                del self.agents[name]
                self.update_tree()
                self.new_agent()
                self.save_to_file()
    
    def save_to_file(self):
        with open('agents.json', 'w') as f:
            json.dump({name: agent.to_dict() for name, agent in self.agents.items()}, f)
    
    def load_from_file(self):
        try:
            with open('agents.json', 'r') as f:
                data = json.load(f)
                self.agents = {name: AgentConfig.from_dict(agent_data) 
                             for name, agent_data in data.items()}
                self.update_tree()
        except FileNotFoundError:
            pass

def main():
    app = QApplication(sys.argv)
    window = AgentManagerUI()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()