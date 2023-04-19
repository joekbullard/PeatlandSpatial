from qgis.core import QgsProcessingProvider
from .algs.peat_point_processing import PeatDepthPoints
from .algs.peatland_code_processing import PeatlandCodeAssessmentBase


class PeatlandSpatialProvider(QgsProcessingProvider):
    def __init__(self):
        super().__init__()
        self.algs = []

    def id(self):
        return "peatlandspatial"

    def name(self):
        return self.tr("Peatland spatial")

    def icon(self):
        return QgsProcessingProvider.icon(self)

    def load(self):
        self.refreshAlgorithms()
        return True

    def getAlgs(self):
        algs = [PeatDepthPoints(), PeatlandCodeAssessmentBase()]
        return algs

    def loadAlgorithms(self):
        self.algs = self.getAlgs()
        for a in self.algs:
            self.addAlgorithm(a)
