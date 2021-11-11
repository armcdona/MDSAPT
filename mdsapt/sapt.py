"""Provide the primary functions."""

from typing import Dict

import pandas as pd

import MDAnalysis as mda
from MDAnalysis.analysis.base import AnalysisBase
from MDAnalysis.topology.guessers import guess_types

import psi4

from .reader import InputReader


class TrajectorySAPT(AnalysisBase):
    """Calculates the <SAPT>`` for individual frames of a trajectory.
    """
    def __init__(self, config: InputReader, **universe_kwargs) -> None:
        self._unv: mda.Universe = mda.Universe(config.top_path, config.trj_path, **universe_kwargs)
        elements = guess_types(self._unv.atoms.names)
        self._unv.add_TopologyAttr('elements', elements)
        self._sel: Dict[mda.AtomGroup] = {x: self._unv.select_atoms(f'resid {x}') for x in config.ag_sel}
        self._sel_pairs = config.ag_pair
        self._mem = config.sys_settings['memory']
        self._cfg = config
        super(TrajectorySAPT, self).__init__(self._unv.trajectory)

    def _prepare(self) -> None:
        self._col = ['residues', 'time', 'energy']
        self.results = pd.DataFrame(columns=self._col)
        self._res_dict = {x: [] for x in self._col}

    def _single_frame(self) -> None:
        xyz_dict = {k: self.get_psi_mol(self._sel[k]) for k in self._sel.keys()}
        with open('test.xyz', 'w+') as r:
            r.write(xyz_dict[2])
        for pair in self._sel_pairs:
            coords = xyz_dict[pair[0]] + '--\n' + xyz_dict[pair[1]] + 'units angstrom'
            dimer = psi4.geometry(coords)
            psi4.set_options({'scf_type': 'df',
                              'freeze_core': 'true'})
            psi4.set_memory(self._mem)

            sapt = psi4.energy('sapt0/jun-cc-pvdz', molecule=dimer)
            result = [f'{pair[0]}-{pair[1]}', self._ts.time, sapt]
            for r in range(len(result)):
                self._res_dict[self._col[r]].append(result[r])

    def _conclude(self) -> None:
        for k in self._col:
            self.results[k] = self._res_dict[k]
