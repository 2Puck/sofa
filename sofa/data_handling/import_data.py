"""
This file is part of SOFA.
SOFA is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

SOFA is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with SOFA.  If not, see <http://www.gnu.org/licenses/>.
"""
from collections import namedtuple
from typing import List, Tuple, NamedTuple, Dict, Union, Callable
import glob
import os
import re

import numpy as np

from igor.binarywave import load as loadibw

def import_bam_ibw_data(
	importParameters: NamedTuple,
	update_progressbar: Callable
) -> Dict:
	"""Try to import data files in bam ibw file format.

	Parameters:
		importParameters(namedtuple): Contains the selected import parameters and options.
		update_progressbar(function): Function to show the import progress.

	Returns: 
		importedData(dict): Contains the imoported curve data and 
		                    if selected additional image or channel data.

	Raises:
		Exception: Can not read the curve data files.
		Exception: Can not read the image file.
		Exception: Image data does not fit the curve data.
		Exception: Can not read the channel file.
		Exception: Channel data does not fit the curve data.
	"""
	importedData = {}

	# Try to import measurement data.
	try:
		CurveData = load_bam_ibw_data_files(
			importParameters,
			update_progressbar
		)
	except Exception as e:
		raise e

	importedData["curveData"] = CurveData

	# Try to import image data if selected.
	if importParameters.filePathImage:
		try:
			ImageData = load_bam_ibw_image_file(
				importParameters,
				update_progressbar
			)
		except Exception as e:
			raise e

		# Test whether the image fits the data.
		if CurveData.m != ImageData.m or CurveData.n != ImageData.n:
			update_progressbar(
				mode="reset",
				value=0,
				label=""
			)
			raise Exception("Image does not fit the data!")

		importedData["imageData"] = ImageData

	# Try to import channel data if selected.
	if importParameters.filePathChannel:
		try:
			ChannelData = load_bam_ibw_channel_data(
				importParameters,
				update_progressbar
			)
		except Exception as e:
			raise e

		# Test whether the channel fits the data.
		if CurveData.m != ChannelData.m or CurveData.n != ChannelData.n:
			update_progressbar(
				mode="reset",
				value=0,
				label=""
			)
			raise Exception("Channel does not fit the data!")

		importedData["channelData"] = ChannelData

	return importedData

def load_bam_ibw_data_files(
	importParameters: NamedTuple,
	update_progressbar: Callable
) -> NamedTuple:
	"""Try to import the .

	Parameters:
		importParameters(namedtuple): Contains the selected import parameters and options.
		update_progressbar(function): Function to show the import progress.

	Returns: 
		CurveData(namedTuple): Contains the .
	"""
	update_progressbar(
		mode="reset",
		value=0,
		label="Importing wave data"
	)

	CurveData = namedtuple(
		"CurveData",
		[
			"filename",
			"approachCurves",
			"retractCurves",
			"m",
			"n"
		]
	)

	m, n = get_data_dimensions(
		importParameters.filePathData
	)
	filename = get_filename(
		importParameters.filePathData
	)
	
	dataFiles = sorted(glob.glob(os.path.join(importParameters.filePathData, "**/*.ibw")))
	
	progressValue = 100 / (len(dataFiles) / 2)

	approachCurves = []
	retractCurves = []

	for i in range(0, len(dataFiles), 2):
		# Load ibw data and remove nan values.
		curveXValues = np.asarray(loadibw(dataFiles[i+1])["wave"]["wData"])
		curveYValues = np.asarray(loadibw(dataFiles[i])["wave"]["wData"])

		# Remove nan values.
		curveValidXValues = curveXValues[~np.isnan(curveXValues)]
		curveValidYValues = curveYValues[~np.isnan(curveYValues)]

		approachCurve, retractCurve = split_curve(
			curveValidXValues, curveValidYValues
		)
		
		approachCurves.append(approachCurve)
		retractCurves.append(retractCurve)
		
		update_progressbar(
			mode="update",
			value=progressValue
		)
		
	return CurveData(
		filename=filename,
		approachCurves=approachCurves,
		retractCurves=retractCurves,
		m=m, 
		n=n
	)

def get_filename(filePathData: str) -> str:
	"""

	Parameters:
		filePathData(str): Filepath to the data dictionary.

	Returns:
		filename(str): Name .
	"""
	return os.path.basename(filePathData)

def get_data_dimensions(filePathData: str) -> Tuple[int, int]:
	"""

	Parameters:
		filePathData(str):

	Returns:
		m(int): .
		n(int): .
	"""
	m = len(
		os.listdir(filePathData)
	)
	n = len(
		os.listdir(
			os.path.join(
				filePathData, 
				os.listdir(filePathData)[0]
			)
		)
	) / 2
	return m, n

def split_curve(
	xValues: np.ndarray, 
	yValues: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
	"""Split measurement curve into an approach and retract part.

	Parameters:
		xValues(np.ndarray): X values of the current curve.
		yValues(np.ndarray): Y values of the current curve.

	Returns:
		approachCurve(list): . 
		retractCurve(list): .
	"""
	# 
	splittingPoint = np.argmax(xValues)
	approachXValues = xValues[:splittingPoint]
	approachYValues = yValues[:splittingPoint]
	# 
	retractXValues = np.flip(xValues[splittingPoint :], 0)
	retractYValues = np.flip(yValues[splittingPoint :], 0)

	approachCurve = [approachXValues, approachYValues]
	retractCurve = [retractXValues, retractYValues]

	return approachCurve, retractCurve

def load_bam_ibw_image_file(
	importParameters: NamedTuple,
	update_progressbar: Callable
) -> NamedTuple:
	"""Try to import an optional image file.
	
	Parameters:
		importParameters(namedtuple): Contains the selected import parameters and options.
		update_progressbar(function): Function to show the import progress.

	Returns:
		ImageData(namedtuple): Contains the image data.

	Raises:
		Exception: Can not read the image file.
	"""
	ImageData = namedtuple(
		"ImageData",
		[
			"filename",
			"m",
			"n",
			"fss",
			"sss",
			"xOffset",
			"yOffset",
			"springConstant",
			"height",
			"adhesion"
		]
	)

	try:
		imageData = loadibw(importParameters.filePathImage)
		imageDataNote = re.split(r'[\r:]', imageData['wave']['note'].decode("utf-8", errors="replace"))
		imageChannelData = np.flip(np.rot90(np.asarray(imageData["wave"]["wData"]), 3), 1)

		return ImageData(
			filename=importParameters.filePathImage.rsplit("/",1)[1].split(".", 1)[0],
			m=imageData['wave']['wave_header']['nDim'][1],
			n=imageData['wave']['wave_header']['nDim'][0],
			fss=imageDataNote[imageDataNote.index("FastScanSize")+1],
			sss=imageDataNote[imageDataNote.index("SlowScanSize")+1],
			xOffset=imageDataNote[imageDataNote.index("XOffset")+1],
			yOffset=imageDataNote[imageDataNote.index("YOffset")+1],
			springConstant=imageDataNote[imageDataNote.index("SpringConstant")+1],
			height=imageChannelData[:, :, 0],
			adhesion=imageChannelData[:, :, 1]
		)
	except ValueError:
		raise Exception("Cant read image data!")

def load_bam_ibw_channel_data(
	importParameters: NamedTuple,
	update_progressbar: Callable
) -> NamedTuple:
	"""Try to import an addtional channel file.
	
	Parameters:
		importParameters(namedtuple): Contains the selected import parameters and options.
		update_progressbar(function): Function to show the import progress.

	Returns:
		ChannelData(namedtuple): Contains the channel data.

	Raises:
		Exception: Can not read the channel file.
	"""
	ChannelData = namedtuple(
		"ChannelData",
		[
			"data",
			"m",
			"n"
		]
	)


def import_sofa_data(
	importParameters: NamedTuple,
	update_progressbar: Callable
) -> None:
	"""Try to import selected data files in sofa file format.

	Parameters:
		importParameters(namedtuple): Contains the selected import parameters and options.
		update_progressbar(function): Function to show the import progress.
	"""
	pass

def restore_sofa_data(
	filePath: str
) -> Dict:
	"""Restore the state of the last SOFA session.
	
	Parameters:
		filePath(str): Path to the backup file.

	Returns:
		backupData(dict): .

	Raises:
		FileNotFoundError: Can not find a backup file.
	"""
	try:
		with open(filePath, 'r+') as dataFile:
			backupData = dataFile.read()

	except FileNotFoundError:
		raise FileNotFoundError

	return json.loads(backupData)


# Defines all available import options.
importFunctions = {
	"BAM_IBW": (import_bam_ibw_data, "*.ibw"),
	"SOFA": (import_sofa_data, "*.json")
}