# Release 1.0.0

#  Copyright (C) 2025 Vojtech Klapetek.
#
#  This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
#  License as published by the Free Software Foundation; either version 3 of the License, or (at your option) any
#  later version.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
#  warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
#  details.

from ij import IJ, ImagePlus, ImageListener
from ij.gui import RoiListener, Roi, Line, ProfilePlot, Plot
from ij.plugin import ContrastEnhancer
from ij.io import SaveDialog
from javax.swing import JFrame, JPanel, JButton, JOptionPane, JLabel, JTextField, BorderFactory, JTextPane, JRadioButton, ButtonGroup, JComboBox, JTextArea
from java.awt import GridBagLayout, GridBagConstraints as GBC
from javax.swing.event import DocumentListener
from java.awt.event import ActionListener, ItemListener, ItemEvent
from java.lang import RuntimeException

# partly based on matplotlib Set1 color scheme
COLORS = ["blue", "green", "red", "orange", "magenta", "#ffff33", "#a65628", "#f781bf", "#999999"]


class FieldListener(DocumentListener, ActionListener):
	def __init__(self, textfields, frame):
		self.textfields = textfields
		self.frame = frame
		self.lane_dir = "vertical"
		self.contrast_enhanced = False
		self.first_x = None # before analysis, set these variables via updateFields()
		self.first_y = None
		self.lane_length = None
		self.lane_sep = None
		self.lane_width = None
		self.lane_count = None
		
		imp = IJ.getImage()
		ip = imp.getProcessor().convertToRGB()
		self.imp = ImagePlus("Lane overview", ip)
		self.orig_ip = self.imp.getProcessor().duplicate()
		
		analysis_ip = ip.duplicate()
		analysis_ip.invert()
		self.analysis_imp = ImagePlus("Analysis", analysis_ip)
		
		self.imp.show()
		
	def updateFields(self):
		try:
			first_x = int(self.textfields["First lane x"].getText())
			first_y = int(self.textfields["First lane y"].getText())
			lane_length = int(self.textfields["Lane length"].getText())
			lane_sep = int(self.textfields["Lane separation"].getText())
			lane_width = int(self.textfields["Lane width"].getText())
			lane_count = int(self.textfields["Lane count"].getText())
		except Exception:
			return
			
		self.first_x = first_x
		self.first_y = first_y
		self.lane_length = lane_length
		self.lane_sep = lane_sep
		self.lane_width = lane_width
		self.lane_count = lane_count

	def lanePreview(self):
		if self.contrast_enhanced:
			ip = self.enhanced_ip.duplicate()
		else:
			ip = self.orig_ip.duplicate()

		for i in range(self.lane_count):
			if self.lane_dir == "vertical":
				roi = Line(self.first_x + i * self.lane_sep, self.first_y,
							self.first_x + i * self.lane_sep, self.first_y + self.lane_length)
			else:
				roi = Line(self.first_x, self.first_y + i * self.lane_sep,
							self.first_x + self.lane_length, self.first_y + i * self.lane_sep)
			
			roi.setStrokeWidth(self.lane_width)

			roi = roi.getPolygon()   # draw as polygon to get rectangle shape instead of line
			ip.setColor(COLORS[i % len(COLORS)])    # (which would have round ends)
			ip.setLineWidth(5)
			ip.drawPolygon(roi)

		self.imp.setProcessor(ip)


	def runAnalysis(self, event):
		self.plot, self.plvalues = analyze(self.first_x, self.first_y, self.lane_length,
											self.lane_sep, self.lane_width, self.lane_count,
											self.lane_dir, self.analysis_imp)
		self.plotWindow = self.plot.show()
		self.plot.savePlotObjects()
		
		background_window(self.frame, self)
		
	def enhanceContrast(self, event):
		self.contrast_enhanced = True
		self.enhanced_ip = self.orig_ip.duplicate()
		enhancer = ContrastEnhancer()
		enhancer.equalize(self.enhanced_ip)
		
		self.lanePreview()

	# following three functions listen to changes in text fields checked by updateFields()
	def changedUpdate(self, event):
		self.updateFields()
		self.lanePreview()
	
	def removeUpdate(self, event):
		self.changedUpdate(event)
	
	def insertUpdate(self, event):
		self.changedUpdate(event)
	
	# this function listens to vertical/horizontal radio button switching
	def actionPerformed(self, event):
		if event.getActionCommand() == "Vertical":
			self.lane_dir = "vertical"
			self.lane_dir_label.setText("Vertical: Assumes analysis lanes are parallel to gel lanes.")
		if event.getActionCommand() == "Horizontal":
			self.lane_dir = "horizontal"
			self.lane_dir_label.setText("Horizontal: Assumes analysis lanes are perpendicular to gel lanes.")
		self.frame.pack()
		self.lanePreview()
		

class BackgroundListener(DocumentListener):
	def __init__(self, textfields, frame, fieldListener):
		self.textfields = textfields
		self.frame = frame
		self.fieldListener = fieldListener
		
		self.first_x = fieldListener.first_x
		self.first_y = fieldListener.first_y
		self.lane_length = fieldListener.lane_length
		self.lane_sep = fieldListener.lane_sep
		self.lane_width = fieldListener.lane_width
		self.lane_count = fieldListener.lane_count
	
	def updateFields(self):
		try:
			bg_x = int(self.textfields["Left background sample x"].getText())
			bg_sep = int(self.textfields["Background sample separation"].getText())
		except Exception:
			return
		
		self.bg_x = bg_x
		self.bg_sep = bg_sep
	
	def backgroundPreview(self):
		self.fieldListener.lanePreview()
		
		ip = self.fieldListener.imp.getProcessor().convertToRGB()

		for i in range(2):
			if self.fieldListener.lane_dir == "vertical":
				roi = Line(self.bg_x + i * self.bg_sep, self.first_y,
							self.bg_x + i * self.bg_sep, self.first_y + self.lane_length)
			else:
				roi = Line(self.bg_x + i * self.bg_sep, self.first_y - 0.5 * self.lane_width,
							self.bg_x + i * self.bg_sep,
							self.first_y + (self.lane_count - 1) * self.lane_sep + 0.5 * self.lane_width)

			roi.setStrokeWidth(5) # TODO implement width setting for background as well?

			ip.setRoi(roi)
			ip.setColor("black")
			ip.draw(roi)
			
		self.fieldListener.imp.setProcessor(ip)
		
		self.fieldListener.plot.restorePlotObjects()
		self.a, self.b, self.c = extract_background(self.bg_x, self.bg_sep, self.first_y, self.lane_length,
													self.fieldListener.lane_dir, self.lane_count,
													self.lane_sep, self.lane_width,
													self.fieldListener.analysis_imp,
													self.fieldListener.plot)
		
	def removeBackground(self, event):
		imp = self.fieldListener.analysis_imp

		plot = Plot("Gel profiles", "Distance (pixels)", "Gray value")
		self.adj_profiles = []

		for i in range(self.lane_count):
			if self.fieldListener.lane_dir == "vertical":
				x = self.first_x + i * self.lane_sep
				roi = Line(x, self.first_y, x, self.first_y + self.lane_length)
			else:
				y = self.first_y + i * self.lane_sep
				roi = Line(self.first_x, y, self.first_x + self.lane_length, y)
				
			roi.setStrokeWidth(self.lane_width)
			imp.setRoi(roi)
			pp = ProfilePlot(imp)
			values = pp.getProfile()
			
			for j in range(self.lane_length):
				if self.fieldListener.lane_dir == "vertical":
					y = self.first_y + j
				else:
					y = i * self.lane_sep + 0.5 * self.lane_width
					x = self.first_x + j
				values[j] = values[j] - (self.a * x + self.b * y + self.c)
			plot.setColor(COLORS[i % len(COLORS)])
			plot.add("line", values)
			self.adj_profiles.append(values)

		self.fieldListener.lanePreview() # removes background lines on gel
		self.fieldListener.plotWindow.close()
		self.plotWindow = plot.show()
		self.adj_plot = plot
		self.adj_plot.savePlotObjects()
		
		measurement_window(self.frame, self)

	# function used for "Back" button
	def revertToPrevStep(self, event):
		self.frame.getContentPane().removeAll()
		self.frame.setTitle("Lane selection")
		self.frame.getContentPane().add(self.fieldListener.panel)
		self.frame.setLocationRelativeTo(None)
		self.frame.pack()
		self.fieldListener.plotWindow.close()
		self.fieldListener.lanePreview()
	
	# following three functions listen to changes in text fields checked by updateFields()
	def changedUpdate(self, event):
		self.updateFields()
		self.backgroundPreview()
	
	def removeUpdate(self, event):
		self.changedUpdate(event)
	
	def insertUpdate(self, event):
		self.changedUpdate(event)
		

class MeasurementListener(DocumentListener, ItemListener):
	def __init__(self, textfields, result_fields, frame, backgroundListener):
		self.textfields = textfields
		self.result_fields = result_fields
		self.frame = frame
		self.backgroundListener = backgroundListener
		self.min_bound = 0
		self.max_bound = self.backgroundListener.lane_length
		self.selectionList = []
		self.addSelectionArea()
		self.selected_i = 0
		
		self.first_x = backgroundListener.first_x
		self.first_y = backgroundListener.first_y
		self.lane_sep = backgroundListener.lane_sep
		self.lane_width = backgroundListener.lane_width
		self.lane_count = backgroundListener.lane_count
		self.adj_plot = self.backgroundListener.adj_plot
		self.adj_profiles = self.backgroundListener.adj_profiles
		self.fieldListener = backgroundListener.fieldListener
	
	def updateFields(self):
		try:
			left_bound = int(self.textfields["Left peak sum border"].getText())
			right_bound = int(self.textfields["Right peak sum border"].getText())
		except Exception:
			return
		
		self.left_bound = left_bound
		self.right_bound = right_bound
		self.selectionList[self.selected_i][0] = left_bound
		self.selectionList[self.selected_i][1] = right_bound
	
	def sumProfiles(self):	
		self.adj_plot.restorePlotObjects()
		self.adj_plot.setColor("black")
		limits = self.adj_plot.getLimits()
		min_y = limits[2]
		max_y = limits[3]
		legend = "	".join(["Lane " + str(i + 1) for i in range(self.lane_count)])
		self.adj_plot.addLegend(legend)
		self.adj_plot.drawLine(self.left_bound, min_y, self.left_bound, max_y)
		self.adj_plot.drawLine(self.right_bound, min_y, self.right_bound, max_y)
		self.adj_plot.update()
		
		for i in range(self.lane_count):
			lane_sum = sum(self.adj_profiles[i][self.left_bound:self.right_bound])
			self.result_fields[i].setText(str(round(lane_sum, 3)))
			
		# display left and right borders on gel
		self.fieldListener.lanePreview()
		
		ip = self.fieldListener.imp.getProcessor().convertToRGB()
		
		if self.fieldListener.lane_dir == "vertical":
			line_ys = [self.first_y + self.left_bound, self.first_y + self.right_bound]
		else:
			line_xs = [self.first_x + self.left_bound, self.first_x + self.right_bound]

		for i in range(2):
			if self.fieldListener.lane_dir == "vertical":
				roi = Line(self.first_x - 0.5 * self.lane_width,
							line_ys[i],
							self.first_x + (self.lane_count - 1) * self.lane_sep + 0.5 * self.lane_width,
							line_ys[i])
			else:
				roi = Line(line_xs[i],
							self.first_y - 0.5 * self.lane_width,
							line_xs[i],
							self.first_y + (self.lane_count - 1) * self.lane_sep + 0.5 * self.lane_width)
			
			roi.setStrokeWidth(5)
			ip.setRoi(roi)
			ip.setColor("black")
			ip.draw(roi)
			
		self.fieldListener.imp.setProcessor(ip)

	def saveMeasurement(self, event):
		save_dialog = SaveDialog("Save peak sums", "results", ".txt")
		directory = save_dialog.getDirectory()
		if directory != None:
			filename = save_dialog.getFileName()
			f = open(directory + "/" + filename, "w")
			results = str("\t".join(["Lane no."] + ["Selection " + str(i + 1) for i in range(len(self.selectionList))])) + "\n"
			for i in range(self.lane_count):
				lane_line = ["Lane " + str(i + 1)]
				for j in range(len(self.selectionList)):
					left_bound = self.selectionList[j][0]
					right_bound = self.selectionList[j][1]
					lane_sum = round(sum(self.backgroundListener.adj_profiles[i][left_bound:right_bound]), 3)
					lane_line.append(str(lane_sum))
				results += "\t".join(lane_line) + "\n"
			f.write(results)
			f.close()
	
	# function used for "Back" button
	def revertToPrevStep(self, event):
		self.frame.getContentPane().removeAll()
		self.frame.setTitle("Lane selection")
		self.frame.getContentPane().add(self.backgroundListener.panel)
		self.frame.setLocationRelativeTo(None)
		self.frame.pack()
		
		self.backgroundListener.plotWindow.close()
		self.fieldListener.plotWindow = self.fieldListener.plot.show()
		
		self.backgroundListener.backgroundPreview()
		
	def addSelectionArea(self):
		self.selectionList.append([self.min_bound, self.max_bound])
	
	# function listens to "add selection area" button
	def addSelectionAreaEvent(self, event):
		self.area_selector.addItem("Selection area " + str(self.area_selector.getItemCount() + 1))
		self.addSelectionArea()
	
	# following three functions listen to changes in text fields checked by updateFields()
	def changedUpdate(self, event):
		self.updateFields()
		self.sumProfiles()
	
	def removeUpdate(self, event):
		self.changedUpdate(event)
	
	def insertUpdate(self, event):
		self.changedUpdate(event)
	
	# function listens to changes in the selected area combo box
	def itemStateChanged(self, event):
		if event.getStateChange() == ItemEvent.SELECTED:
			self.selected_i = event.getItemSelectable().getSelectedIndex()
			lb, rb = self.selectionList[self.selected_i][0], self.selectionList[self.selected_i][1]
			self.textfields["Left peak sum border"].setText(str(lb))
			self.textfields["Right peak sum border"].setText(str(rb))
			
			self.sumProfiles()


# Parameters:
# lane_direction: "vertical" / "horizontal"
def analyze(first_x, first_y, lane_length, lane_sep, lane_width, lane_count, lane_direction, imp):
	plot = Plot("Gel profiles", "Distance (pixels)", "Gray value")
	plvalues = []

	for i in range(lane_count):
		if lane_direction == "vertical":
			roi = Line(first_x + i*lane_sep, first_y, first_x + i*lane_sep, first_y + lane_length)
		else:
			roi = Line(first_x, first_y + i*lane_sep, first_x + lane_length, first_y + i*lane_sep)

		roi.setStrokeWidth(lane_width)
		imp.setRoi(roi)
		pp = ProfilePlot(imp)
		plvalues.append(pp.getProfile())

		plot.setColor(COLORS[i % len(COLORS)])
		plot.add("line", plvalues[i])

	return plot, plvalues

# Parameters:
# lane_direction: "vertical" / "horizontal"
def extract_background(bg_x, bg_sep, first_y, lane_length, lane_direction, lane_count, lane_sep, lane_width, imp, plot=None):
	plvalues = {}
	
	for i in range(2):
		for x_offset in range(-2, 3): # get multiple lines instead of average over five pixels
			if lane_direction == "vertical":
				roi = Line(bg_x + i*bg_sep + x_offset, first_y,
							bg_x + i*bg_sep + x_offset, first_y + lane_length)
			else:
				y_offset = 0.5*lane_width
				roi = Line(bg_x + i*bg_sep + x_offset, first_y - y_offset,
							bg_x + i*bg_sep + x_offset, first_y + (lane_count - 1)*lane_sep + y_offset)
			
			imp.setRoi(roi)
			pp = ProfilePlot(imp)
			plvalues[bg_x + i*bg_sep + x_offset] = pp.getProfile()
	
	a, b, c = fit_plane(plvalues)

	if plot:
		for i in range(2):
			plot.setColor("black")
			if lane_direction == "vertical": # lines on graph represent background estimate at the background lines on gel
				x = bg_x + i*bg_sep
				bg_values = [x*a + y*b + c for y in range(lane_length)]
			else: # lines on graph represent background estimate at the highest and lowest lane
				y = i*(lane_count - 1)*lane_sep + 0.5*lane_width
				bg_values = [(x + bg_x)*a + y*b + c for x in range(lane_length)]
			plot.add("line", bg_values)
	
	return a, b, c

# function based on Gwyddion level.c module, Copyright (C) David Necas (Yeti), Petr Klapetek
# values: dict with for each absolute x, a list of values with relative y = 0 to y = len(list)
def fit_plane(values):
	sum_x = 0
	sum_y = 0
	sum_z = 0
	sum_xx = 0
	sum_yy = 0
	sum_xy = 0
	sum_xz = 0
	sum_yz = 0
	n = 0

	for x, z_list in values.items():
		sum_x += x*len(z_list)
		sum_xx += x**2 * len(z_list)
		sum_y += len(z_list)*(len(z_list) - 1)/2
		sum_yy += (2 * len(z_list)**3 - 3 * len(z_list)**2 + len(z_list))/6
		n += len(z_list)
		y = 0
		for z in z_list:
			sum_z += z
			sum_xy += x*y
			sum_xz += x*z
			sum_yz += y*z
			y += 1
	
	det = (n*sum_xx*sum_yy) + (2*sum_x*sum_xy*sum_y) - (sum_x*sum_x*sum_yy) -(sum_y*sum_y*sum_xx) - (n*sum_xy*sum_xy)
	if det == 0:
		a = 0
		b = 0
		c = 0
	else:
		det = 1.0/det
		alpha_1 = (n*sum_yy) - (sum_y*sum_y)
		alpha_2 = (n*sum_xx) - (sum_x*sum_x)
		alpha_3 = (sum_xx*sum_yy) - (sum_xy*sum_xy)
		beta_1 = (sum_x*sum_y) - (n*sum_xy)
		beta_2 = (sum_x*sum_xy) - (sum_xx*sum_y)
		gamma_1 = (sum_xy*sum_y) - (sum_x*sum_yy)
		
		a = det*(alpha_1*sum_xz + beta_1*sum_yz + gamma_1*sum_z)
		b = det*(beta_1*sum_xz + alpha_2*sum_yz + beta_2*sum_z)
		c = det*(gamma_1*sum_xz + beta_2*sum_yz + alpha_3*sum_z)

	return a, b, c


def selection_window():
	try:
		IJ.getImage()
	except RuntimeException:
		return
		
	frame = JFrame("Lane selection", visible=True)

	panel = JPanel()
	panel.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10))
	gb = GridBagLayout()
  	panel.setLayout(gb)  
  	gc = GBC()
  	
  	gc.gridx = 0
  	gc.gridy = 0
  	gc.gridwidth = 1 
  	gc.gridheight = 1
  	gc.fill = GBC.NONE
  	
  	textfields = {}
  	field_listener = FieldListener(textfields, frame)
  	
  	analysis_defaults = {"First lane x": 815, "First lane y": 50, "Lane length": 950,
					"Lane separation": 165, "Lane width": 50, "Lane count": 5}
  	
  	button = JButton("Auto-adjust contrast", actionPerformed=field_listener.enhanceContrast)
	gb.setConstraints(button, gc)
	panel.add(button)
	
	gc.gridy += 1
	
	label = JLabel("<html><b>Lane direction</b></html>")
	gb.setConstraints(label, gc)
	panel.add(label)
	gc.gridy += 1
	
	vert_button = JRadioButton("Vertical")
	vert_button.setSelected(True)
	gb.setConstraints(vert_button, gc)
	panel.add(vert_button)
	vert_button.addActionListener(field_listener)
	
	gc.gridx = 1
	
	hor_button = JRadioButton("Horizontal")
	gb.setConstraints(hor_button, gc)
	panel.add(hor_button)
	hor_button.addActionListener(field_listener)
	
	button_group = ButtonGroup()
	button_group.add(vert_button)
	button_group.add(hor_button)
	gc.gridx = 0
	gc.gridy += 1
	
	gc.gridwidth = 2
	label = JLabel("Vertical: Assumes analysis lanes are parallel to gel lanes.")
	gb.setConstraints(label, gc)
	panel.add(label)
	field_listener.lane_dir_label = label
	
	gc.gridwidth = 1
	gc.gridy += 1

	for title in ["First lane x", "First lane y", "Lane length", "Lane separation", "Lane width", "Lane count"]:  
	    gc.gridx = 0  
	    gc.anchor = GBC.EAST  
	    label = JLabel(title + ": ")  
	    gb.setConstraints(label, gc)
	    panel.add(label)
	    
	    gc.gridx = 1
	    gc.anchor = GBC.WEST
	    text = str(analysis_defaults[title]) 
	    textfield = JTextField(text, 10)
	    textfields[title] = textfield
	    gb.setConstraints(textfield, gc)
	    textfield.getDocument().addDocumentListener(field_listener)
	    panel.add(textfield)

	    gc.gridy += 1

	gc.gridx = 1
	button = JButton(">> Background selection", actionPerformed=field_listener.runAnalysis)
	gb.setConstraints(button, gc)
	panel.add(button)
	frame.getContentPane().add(panel)
	frame.setLocationRelativeTo(None)
	frame.pack()
	frame.toFront()
	
	field_listener.panel = panel
	field_listener.updateFields()
	field_listener.lanePreview()


def background_window(frame, field_listener):
	frame.getContentPane().removeAll()
	frame.setTitle("Background selection")
	panel = JPanel()
	panel.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10))
	gb = GridBagLayout()
  	panel.setLayout(gb)  
  	gc = GBC()
  	
  	gc.gridx = 0
  	gc.gridy = 0
  	gc.gridwidth = 1
  	gc.gridheight = 1
  	gc.fill = GBC.NONE
  	
  	gc.gridwidth = 2
  	label_text = "Place the black lines on the lane overview image so that they are located outside of any gel lane, one to the left from your selection lanes, one to the right. These lines are then used to fit a background plane, which will be subtracted from the data. You may see a preview of the background for the two lines in the gel profile graph."
  	label = JLabel("<html>" + label_text + "</html>")
  	label = JTextArea(label_text, 6, 30)
  	label.setLineWrap(True)
  	label.setWrapStyleWord(True)
  	label.setEditable(False)
  	gb.setConstraints(label, gc)
  	panel.add(label)
  	
  	gc.gridwidth = 1
  	gc.gridy += 1
  	
  	textfields = {}
	bg_listener = BackgroundListener(textfields, frame, field_listener)
	
	if field_listener.lane_dir == "vertical":
		background_defaults = {
			"Left background sample x": int(field_listener.first_x - 0.5 * field_listener.lane_sep),
			"Background sample separation": field_listener.lane_count * field_listener.lane_sep
			}
	else:
		background_defaults = {
			"Left background sample x": int(field_listener.first_x - 0.5 * field_listener.lane_sep),
			"Background sample separation": field_listener.lane_length + field_listener.lane_sep}
		

	for title in ["Left background sample x", "Background sample separation"]:  
	    gc.gridx = 0  
	    gc.anchor = GBC.EAST  
	    label = JLabel(title + ": ")  
	    gb.setConstraints(label, gc)
	    panel.add(label)

	    gc.gridx = 1
	    gc.anchor = GBC.WEST
	    text = str(background_defaults[title]) 
	    textfield = JTextField(text, 10)
	    textfields[title] = textfield
	    gb.setConstraints(textfield, gc)
	    textfield.getDocument().addDocumentListener(bg_listener)
	    panel.add(textfield)
	    gc.gridy += 1

	gc.gridx = 0
	button = JButton("<< Back", actionPerformed=bg_listener.revertToPrevStep)
	gb.setConstraints(button, gc)
	panel.add(button)

	gc.gridx = 1
	button = JButton(">> Remove background", actionPerformed=bg_listener.removeBackground)
	gb.setConstraints(button, gc)
	panel.add(button)
	frame.getContentPane().add(panel)
	frame.setLocationRelativeTo(None)
	frame.pack()
	frame.toFront()
	
	bg_listener.panel = panel
	bg_listener.updateFields()
	bg_listener.backgroundPreview()


def measurement_window(frame, background_listener):
	max_length = len(background_listener.adj_profiles[0]) - 1
	
	frame.getContentPane().removeAll()
	frame.setTitle("Measurement")
	panel = JPanel()
	panel.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10))
	gb = GridBagLayout()
  	panel.setLayout(gb)  
  	gc = GBC()

  	gc.gridx = 0
  	gc.gridy = 0
  	gc.gridwidth = 1 
  	gc.gridheight = 1
  	gc.fill = GBC.NONE

  	textfields = {}
	result_fields = []
	ms_listener = MeasurementListener(textfields, result_fields, frame, background_listener)
	
	combobox = JComboBox(["Selection area 1"])
	gb.setConstraints(combobox, gc)
	panel.add(combobox)
	ms_listener.area_selector = combobox
	combobox.addItemListener(ms_listener)
	
	gc.gridx = 1
	button = JButton("Add area", actionPerformed=ms_listener.addSelectionAreaEvent)
	gb.setConstraints(button, gc)
	panel.add(button)
	gc.gridy += 1
	

	measurement_defaults = {
		"Left peak sum border": 0,
		"Right peak sum border": max_length
		}
	
	for title in ["Left peak sum border", "Right peak sum border"]:  
	    gc.gridx = 0  
	    gc.anchor = GBC.EAST  
	    label = JLabel(title + ": ")  
	    gb.setConstraints(label, gc) 
	    panel.add(label)  

	    gc.gridx = 1
	    gc.anchor = GBC.WEST
	    text = str(measurement_defaults[title]) 
	    textfield = JTextField(text, 10)
	    textfields[title] = textfield
	    gb.setConstraints(textfield, gc)
	    textfield.getDocument().addDocumentListener(ms_listener)
	    panel.add(textfield)
	    gc.gridy += 1

	for i in range(1, ms_listener.lane_count + 1):
	    gc.gridx = 0  
	    gc.anchor = GBC.EAST  
	    label = JLabel("Lane " + str(i) + ": ")
	    gb.setConstraints(label, gc)
	    panel.add(label)
	    
	    gc.gridx = 1
	    gc.anchor = GBC.WEST  
	    result_field = JTextPane()
	    result_field.setContentType("text/html")
	    result_field.setEditable(False)
	    result_field.setBackground(None)
	    result_field.setBorder(None)
	    gb.setConstraints(result_field, gc)
	    panel.add(result_field)
	    result_fields.append(result_field)
	    
	    gc.gridy += 1

	gc.gridx = 0
	button = JButton("<< Back", actionPerformed=ms_listener.revertToPrevStep)
	gb.setConstraints(button, gc)
	panel.add(button)

	gc.gridx = 1
	button = JButton("Save measurement", actionPerformed=ms_listener.saveMeasurement)
	gb.setConstraints(button, gc)
	panel.add(button)

	frame.getContentPane().add(panel)
	frame.setLocationRelativeTo(None)
	frame.pack()
	frame.toFront()
	
	ms_listener.updateFields()
	ms_listener.sumProfiles()
	

selection_window()
