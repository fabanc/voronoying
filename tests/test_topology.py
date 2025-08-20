from unittest import TestCase, main
import os
import arcpy
from src.topology import validate_topology

xmldir = r"data\input" # xml files location
workspace =  r"data\output\inputs.gdb" # in_memory?
dataset_path = r"data\output\output.gdb"

class TestTopology(TestCase):
    @classmethod
    def setUpClass(cls):
        """ set up the workspaces using the XML files"""
        print("Importing XML to workspaces")
        arcpy.env.overwriteOutput = "True"
        parentdir = os.path.dirname(workspace)
        arcpy.management.CreateFileGDB(parentdir, os.path.basename(workspace))
        arcpy.management.CreateFileGDB(parentdir, os.path.basename(dataset_path))
        test_name = None
        # xml files for tests, kept small. 
        for fn in os.listdir(xmldir):
            if fn.lower().startswith('topo_test') and fn.lower().endswith('.xml'):
                test_name = fn
                cls.loadXML(workspace, os.path.join(xmldir, fn), fn)
            if test_name is not None:
                break
        if test_name is None:
            print("failed to load XML")

        arcpy.env.workspace = workspace

    @classmethod
    def tearDownClass(cls):
        print("Cleaning up")
        try:
            arcpy.management.Delete(workspace)
            arcpy.management.Delete(dataset_path)
        except:
            print("failed to delete gdb, check locks")

    @classmethod
    def loadXML(cls, gdb, xml, filename):
        """
        import feature classes from xml documents, retain a list of the gold features
        :param gdb: full path for the working geodatabase
        :param xml: full path to the xml
        """

        arcpy.env.workspace = gdb

        try:
            arcpy.management.ImportXMLWorkspaceDocument(gdb, xml, "DATA", "DEFAULTS")
            print(f"Import of {filename} successful.")
        except Exception as e:
            print(f"Failed to import {filename}: {str(e)}")
            cls.assertFalse(True)

    def checkTopoResults(self, expected, errors, count):
        if errors is not None:
            self.assertEqual(len(errors), count)
            for e in errors:
                self.assertIn(e, expected)
        else:
            self.fail("failed to yield topology results")
    
    def test_point_only(self):
        try:
            validate_topology(workspace + "/fishnet_points_good", None, 10, dataset_path)
        except ValueError:
            pass
        except Exception:
           self.fail("Unexpected exception was raised")
        else:
           self.fail("Expected ValueError not raised")

    def test_line_only(self):
        try:
            validate_topology(None, workspace + "/fishnet_lines_good", 10, dataset_path)
        except ValueError:
            pass
        except Exception:
           self.fail("Unexpected exception was raised")
        else:
           self.fail("expected ValueError not raised")

    def test_good(self):
        errors = validate_topology(workspace + "/fishnet_points_good", workspace + "/fishnet_lines_good", 10, dataset_path)
        self.checkTopoResults({}, errors, 0)

    def test_intersect(self):
        expected = { "esriTRTLineNoIntersectOrInteriorTouch" : 1 }
        errors = validate_topology(workspace + "/fishnet_points_good", workspace + "/fishnet_lines_intersect", 10, dataset_path)
        self.checkTopoResults(expected, errors, 1)
    
    def test_duplicates(self):
        expected = { "esriTRTLineNoIntersectOrInteriorTouch" : 2, "esriTRTLineNoOverlap" : 2 } #NOTE: the presence of NoOverlap seems to override yield of esriTRTLineNoSelfOverlap
        errors = validate_topology(workspace + "/fishnet_points_good", workspace + "/fishnet_lines_duplicates", 10, dataset_path)
        self.checkTopoResults(expected, errors, 2)
    
    def test_point_covered_line(self):
        expected = { "esriTRTPointCoveredByLineEndpoint" : 1 }
        errors = validate_topology(workspace + "/fishnet_points_intersects_bad", workspace + "/fishnet_lines_good", 10, dataset_path)
        self.checkTopoResults(expected, errors, 1)

    def test_lowres(self):
        # expect warning but no topology error
        errors = validate_topology(workspace + "/fishnet_points_lowres", workspace + "/fishnet_lines_lowres", 10, dataset_path)
        self.checkTopoResults({}, errors, 0)

def run_tests():
    main()

if __name__ == '__main__':
    run_tests()
