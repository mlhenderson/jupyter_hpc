from distutils.core import setup

setup(
    name='kale_workflows',
    version='0.2',
    license='BSD',
    description='Jupyter HPC Workflows',
    packages={'kale','kale.services','kale.widgets'},
    install_requires=[
        'bqplot>=0.11.0',
        'fireworks>=1.6.9',
        'ipython>=6.1.0',
        'ipywidgets>=7.2.1',
        'networkx>=1.11',
        'numpy>=1.12',
        'pandas>=0.20.3',
        'plotly>=3.1.0',
        'psutil>=5.3.1',
        'requests>=2.18.4',
        'sanic>=0.7.0',
        'traitlets>=4.3.2'
    ]
)
