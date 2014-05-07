from __future__ import division
import numpy
import scipy.sparse
from collections import OrderedDict

from GeoMACH.PGM.configurations import Configuration


class ConfigurationMACH(Configuration):

    def __init__(self):
        super(ConfigurationMACH, self).__init__()
        self.points = OrderedDict()
        self.jacobians = OrderedDict()
        self.updated = {}

    def addPointSet(self, points, pt_name, origConfig=True, **kwargs):
        points = numpy.array(points).real.astype('d')
        self.points[pt_name] = points

        surf, indu, indv = self.oml0.evaluateProjection(points)
        self.jacobians[pt_name] = self.oml0.evaluateBases(surf, indu, indv)

        self.updated[pt_name] = False

    def setDesignVars(self, dv_dict):
        for dv in self.dvs.values():
            dv.vec[:] = numpy.atleast_1d(dv_dict[dv.name]).reshape(dv.shape, order='F')

        for pt_name in self.updated:
            self.updated[pt_name] = False

    def getValues(self):
        dv_dict = {}
        for dv in self.dvs.values():
            dv_dict[dv.name] = dv.vec.reshape(dv.size, order='F')

    def update(self, pt_name, childDelta=True):
        self.compute()
        self.points[pt_name] = self.jacobians[pt_name].dot(self.oml0.C)
        self.updated[pt_name] = True

    def pointSetUpToDate(self, pt_name):
        return self.updated[pt_name]

    def getVarNames(self):
        return list(self.dvs.keys())

    def getNDV(self):
        num_dv = 0
        for dv in self.dvs.values():
            num_dv += dv.size

    def totalSensitivity(self, dfunc_dpt_T, pt_name, comm=None, child=False, nDVStore=0):
        dfunc_dpt_T = numpy.atleast_3d(dfunc_dpt_T)
        num_func = dfunc_dpt.shape[2]
        num_dv = self.getNDV()
        num_pt = self.points[pt_name].shape[0]
        nQ = self.oml0.nQ

        dfunc_ddv_T = numpy.zeros((num_dv, num_func))
        ones = numpy.ones(oml0.nQ)
        lins = numpy.array(numpy.linspace(0, nQ-1, nQ), int)
        for k in range(3):
            P = scipy.sparse.csr_matrix((ones, (lins, lins + k*nQ)), 
                                        shape=(nQ, 3*nQ))
            dfunc_ddv_T[:,:] += self.jacobians[pt_name].dot(self.oml0.M.dot(P.dot(self.jac))).transpose().dot(dfunc_dpt_T)

        return self.convertSensitivityToDict(dfunc_ddv_T)

    def convertSensitivityToDict(self, dfunc_ddv_T):
        dfunc_ddv = {}

        start, end = 0, 0
        for dv in self.dvs.values():
            end += dv.size
            dfunc_ddv[dv.name] = dfunc_ddv_T[start:end].squeeze().T
            start += dv.size

        return dfunc_ddv

    def addVariablesPyOpt(self, optProb):
        for dv in self.dvs.values():
            optProb.addVarGroup(dv.name, dv.size, 'c', 
                                value=dv.val, lower=dv.lower, upper=dv.upper,
                                scale=dv.scale)
        