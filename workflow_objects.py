# Oliver Evans
# August 7, 2017

import bqplot as bq
import networkx
import numpy as np
import ipywidgets as ipw
from copy import copy, deepcopy
from IPython.display import display, HTML

class Workflow(object):
    def __init__(self, name):
        self.dag = networkx.graph.Graph()
        self.name = name
        self.index_dict = {}
        #self.fig_layout = ipw.Layout(width='600px', height='800px')
        self.fig_layout = ipw.Layout(width='1000px', height='800px')
        self._task_names = []
    
    def add_task(self, task, dependencies=None):
        """
        Add instantiated Task object to the Workflow.
        If dependencies=None, then this task will be executed
        as soon as possible upon starting the Workflow.
        A Task may appear only once per Workflow.
        """
        
        # Ensure that tasks are not repeated.
        if task in self.dag.nodes():
            raise ValueError("Task already present in Workflow. Please pass a deepcopy if you wish to repeat the Task.")
        elif task.name in self._task_names:
            raise ValueError("Task name '{}' already present in Workflow. Please use a unique name.".format(task.name))
            
        # Determine index for this Task in this Workflow
        index = self.dag.number_of_nodes()
        # Inform workflow and task of this assignment
        self.dag.add_node(task, index=index)
        task.index[self] = index
        
        if dependencies is not None:
            for dependency in dependencies:
                self.dag.add_edge(dependency, task)
                
    def get_task_by_name(self, name):
        "Return the Task object with the given name in this Workflow."
        for task in self.dag.nodes():
            try:
                if task.name == name:
                    return task
            except AttributeError:
                print("{} has no name.".format(task))

    def _gen_bqgraph(self):
        "Generate bqplot graph."
        
        pos = networkx.nx_pydot.graphviz_layout(self.dag, prog='dot')
        N = self.dag.number_of_nodes()
        
        x, y = [[pos[node][i] for node in self.dag.nodes()] for i in range(2)]

        node_data = [
            {
                'label': str(node.index[self]),
                'shape': 'rect',
                **node.get_user_dict()
            }
            for node in self.dag.nodes()
        ]
        link_data = [
            {
                'source': source.index[self],
                'target': target.index[self]
            } 
            for source, target in self.dag.edges()
        ]

        xs = bq.LinearScale()
        ys = bq.LinearScale()
        scales = {'x': xs, 'y': ys}
        
        graph = bq.Graph(
            node_data=node_data,
            link_data=link_data,
            scales=scales,
            link_type='line',
            highlight_links=False,
            x=x, y=y,
            selected_style={'stroke':'red'}
            #interactions = {
            #    'click': 'tooltip',
            #    'hover': 'select'
            #},
        )
        
        # graph.tooltip = bq.Tooltip(
        #     fields=self.dag.nodes()[0].user_fields
        # )
        
        return graph
    
    def get_bqgraph(self):
        "Retrieve, but do not regenerate bqplot graph."
        return self._bqgraph
    
    def draw_dag(self, layout=None):
        "Return bqplot figure representing DAG, regenerating graph."
        
        self._bqgraph = self._gen_bqgraph()
        
        graph = self.get_bqgraph()
        if layout == None:
            layout = self.fig_layout
            
        fig = bq.Figure(marks=[graph], layout=layout)
                        
        toolbar = bq.Toolbar(figure=fig)
        
        return ipw.VBox([fig, toolbar])
        

class Task(object):
    "One step in a Workflow. Must have a unique name."
    def __init__(self, name, input_files=[], output_files=[], 
                 params={}, num_cores=1, task_type='',
                substitute_strings=[], substitute_lists=[],
                user_fields=[]):
        
        # Name of task (must be unique)
        self.name = name
        
        # Type of task (Notebook, CommandLine, etc.)
        self.task_type = task_type
        
        # List of other Tasks which must complete 
        # before this Task can be run.
        self.dependencies = []
        
        # List of Tasks which depend on this Task.
        self.children = []
        
        # Files which this Task takes as input 
        # and must be present before run.
        self.input_files = input_files
        
        # Files which are generated or modified by this Taks.
        self.output_files = output_files
        
        # Number of CPU cores to run the task on
        self.num_cores = num_cores
        
        # Map workflow to the node index which
        # represents this task in that workflow.
        # Tasks may be in multiple workflows,
        self.index = {}
        
        # Parameters to replace in other arguments
        self.params = params
        
        # List of names of fields to substitute params.
        # If a child class calls Task.__init__ with
        # substitute_strings or substitute_lists as
        # nonempty lists, they will be included here.
        self._substitute_strings = [
            'name',
            'task_type'
        ] + substitute_strings
        self._substitute_lists = [
            'input_files',
            'output_files'
        ] + substitute_lists
        
        self._substitute_fields()
        
        # Fields which are of interest to the user
        self.user_fields = [
            'name', 
            'task_type', 
            'input_files', 
            'output_files',
            'num_cores'
        ] + user_fields
    
    def get_user_dict(self):
        "Generate dictionary of user field names and values"
        return {
            field: getattr(self, field) 
            for field in self.user_fields
        }
            
    def _substitute_fields(self):
        "Replace fields according to params dict."
        for field in self._substitute_strings:
            # Read current value
            before = getattr(self,field)
            # Replace fields
            after = before.format(**self.params)
            # Write new value
            setattr(self, field, after)
            
        for list_name in self._substitute_lists:
            field_list = getattr(self, list_name)
            # Read current values
            for i, before in enumerate(field_list):
                # Replace fields
                after = before.format(**self.params)
                # Write to working copy of list
                field_list[i] = after
            # Write working copy to actual list
            setattr(self, list_name, field_list)
                
    def _run(self):
        """
        Run this Task. Should be executed by a Workflow.
        This function should be overloaded by child classes.
        """
        print("Task run.")
        

class NotebookTask(Task):
    """
    
    Jupyter Notebook which should appear as a node in the Workflow DAG.
    If interactive == True, a kernel will be started and the
    notebook will be opened for user to interact with.
    Workflow will be blocked in the meantime.
    If false, notebook will be executed without opening,
    and Workflow will continue upon successful execution.
    """
    def __init__(self, name, interactive=True, **kwargs):
        self.task_type = 'NotebookTask'
        self.interactive = interactive
        
        user_fields = ['interactive']
        
        super().__init__(
            name=name,
            user_fields=user_fields,
            **kwargs)
    
    def _run(self):
        print("Notebook run.")
    
    def _unblock(self):
        """
        Return control to Workflow after interactive notebook
        execution is complete.
        """
        pass

    
class CommandLineTask(Task):
    "Command Line Task to be executed as a Workflow step."
    def __init__(self, name, command, **kwargs):
        
        self.command = command
        
        user_fields = ['command']
        
        super().__init__(
            name=name,
            task_type='CommandLineTask',
            substitute_strings=['command'],
            user_fields=user_fields,
            **kwargs
        )
        
    
    def _run(self):
        print("Command Line run.")

        
class PythonFunctionTask(Task):
    "Python function call to be executed as a Workflow step."
    def __init__(self, name, fun, fun_args, fun_kwargs, **kwargs):
        # Actual callable function to be executed.
        self.fun = fun
        
        user_fields = ['fun_args', 'fun_kwargs']
        
        super().__init__(
            name=name, 
            task_type='PythonFunctionTask',
            user_fields=user_fields,
            **kwargs
        )
    
    def _run(self):
        print("Python function run.")
        return self.fun(*fun_args, **fun_kwargs)
    
class BatchTask(Task):
    "Task which will be submitted to a batch queue to execute."
    def __init__(self, name, batch_script, **kwargs):
        self.batch_script = batch_script
        
        user_fields = ['batch_script']
        
        super().__init__(
            name=name, 
            task_type='BatchTask',
            user_fields=user_fields,
            **kwargs
        )
        
    def _run(self):
        print("Batch run.")
