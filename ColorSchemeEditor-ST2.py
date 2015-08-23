import sublime, sublime_plugin, os.path

# globals suck, but don't know how to pass data between the classes
_schemeEditor = None
_skipOne = 0
_wasSingleLayout = None
_lastScope = None
_lastScopeIndex = 0

def find_matches ( scope, founds ):
	global _schemeEditor

	ret = []
	maxscore = 0
	# find the scope in the xml that matches the most

	for found in founds:
		foundstr = _schemeEditor.substr( found )
		pos = foundstr.find( '<string>' ) + 8
		foundstr = foundstr[ pos : -9 ]
		foundstrs = foundstr.split( ',' )
		fstrlen = 0
		for fstr in foundstrs:
			fstrlen = len( fstr )
			fstr = fstr.lstrip( ' ' )
			padleft = fstrlen - len( fstr )
			fstr = fstr.rstrip( ' ' )
			score = sublime.score_selector( scope, fstr )
			# print( fstr, score )
			if score > 0:
				a = found.a + pos + padleft
				ret.append( [ score, sublime.Region( a, a + len( fstr ) ) ] )
			pos += fstrlen + 1

	if len( ret ) == 0:
		return None
	else:
		return ret

def display_scope ( region ):
	global _schemeEditor
	# doest change the selection if previous selection was on the same line
	sel = _schemeEditor.sel()
	sel.clear()
	sel.add( region )
	_schemeEditor.show_at_center( region )


def update_view_status ( view ):

	global _lastScope, _lastScopeIndex

	found = None
	_lastScope = []
	_lastScopeIndex = 0
	
	# find the scope under the cursor
	scope_name = view.scope_name( view.sel()[0].a )
	pretty_scope = scope_name.strip( ' ' ).replace( ' ', ' > ' )
	scopes = reversed( pretty_scope.split( ' > ' ) )
	
	# convert to regex and look for the scope in the scheme editor
	for scope in scopes:
		if len( scope ) == 0:
			continue
		dots = scope.count( '.' )
		regex = '<key>scope</key>\\s*<string>([a-z\\.\\-]* ?, ?)*([a-z\\.\\- ]*'
		regex += scope.replace( '.', '(\\.' )
		while dots > 0:
			regex += ')?'
			dots -= 1
		regex += ')( ?, ?[a-z\\.\\-]*)*</string>'

		# print( regex )
		found = _schemeEditor.find_all( regex, 0 )
		found = find_matches( scope_name, found )
		# print( found )
		if found != None:
			_lastScope += found

	# print( _lastScope )
	scopes = len( _lastScope )
	sublime.status_message( 'matches ' + str( scopes ) + ': ' + pretty_scope )
	if scopes == 0:
		_lastScope = None
		display_scope( sublime.Region( 0, 0 ) )
	else:
		_lastScope.sort( key = lambda f: f[1].a )
		_lastScope.sort( key = lambda f: f[0], reverse = True )
		display_scope( _lastScope[0][1] )


def kill_scheme_editor ():
	global _schemeEditor, _skipOne, _wasSingleLayout, _lastScope, _lastScopeIndex
	if int( sublime.version() ) > 3000 and _wasSingleLayout != None:
		_wasSingleLayout.set_layout( {
			'cols': [0.0, 1.0],
			'rows': [0.0, 1.0],
			'cells': [[0, 0, 1, 1]]
		} )
	_skipOne = 0
	_wasSingleLayout = None
	_schemeEditor = None
	_lastScope = None
	_lastScopeIndex = 0


# listeners to update our scheme editor
class NavigationListener ( sublime_plugin.EventListener ):

	def on_close ( self, view ):
		global _schemeEditor
		if _schemeEditor != None:
			if _schemeEditor.id() == view.id():
				kill_scheme_editor()

	def on_selection_modified ( self, view ):
		global _schemeEditor, _skipOne
		if _schemeEditor != None:
			if _schemeEditor.id() != view.id() and not view.settings().get( 'is_widget' ):
				# for some reason this callback is called twice - for mouse down and mouse up
				if _skipOne == 1:
					_skipOne = 0
				else:
					_skipOne = 1
					update_view_status( view )


class EditColorSchemeNextScopeCommand ( sublime_plugin.TextCommand ):
	def run ( self, edit ):
		global _schemeEditor, _lastScope, _lastScopeIndex

		if _schemeEditor != None and _lastScope != None:
			scopes = len( _lastScope )
			if scopes > 1:
				_lastScopeIndex += 1
				if _lastScopeIndex == scopes:
					_lastScopeIndex = 0
				display_scope( _lastScope[_lastScopeIndex][1] )
			sublime.status_message( 'Scope ' + str( _lastScopeIndex + 1 ) + ' of ' + str( scopes ) )



class EditColorSchemePrevScopeCommand ( sublime_plugin.TextCommand ):
	def run ( self, edit ):
		global _schemeEditor, _lastScope, _lastScopeIndex

		if _schemeEditor != None and _lastScope != None:
			scopes = len( _lastScope )
			if scopes > 1:
				if _lastScopeIndex == 0:
					_lastScopeIndex = scopes - 1
				else:
					_lastScopeIndex -= 1
				display_scope( _lastScope[_lastScopeIndex][1] )
			sublime.status_message( 'Scope ' + str( _lastScopeIndex + 1 ) + ' of ' + str( scopes ) )


class EditCurrentColorSchemeCommand ( sublime_plugin.TextCommand ):
	
	def run ( self, edit ):
		global _schemeEditor, _wasSingleLayout
		
		view = self.view
		viewid = view.id()
		window = view.window()
		if _schemeEditor == None:

			# see if not trying to edit on the scheme file
			path = os.path.abspath( sublime.packages_path() + '/../' + view.settings().get( 'color_scheme' ) )
			if path == view.file_name():
				sublime.status_message( 'Select different file from the scheme you want to edit' )
				_schemeEditor = None
				return

			# see if we openeded a new view
			views = len( window.views() )
			_schemeEditor = window.open_file( path )
			if _schemeEditor == None:
				sublime.status_message( 'Could not open the scheme file' )
				return
			if views == len( window.views() ):
				views = 0
			else:
				views = 1

			# if we have only one splitter, open new one
			groups = window.num_groups()
			group = -1
			index = 0
			if groups == 1:
				_wasSingleLayout = window
				group = 1
				window.set_layout( {
					'cols': [0.0, 0.5, 1.0],
					'rows': [0.0, 1.0],
					'cells': [[0, 0, 1, 1], [1, 0, 2, 1]]
				} )
			elif views == 1:
				activegrp = window.active_group() + 1
				if activegrp == groups:
					group = activegrp - 2
					index = len( window.views_in_group( group ) )
				else:
					group = activegrp

			if groups == 1 or views == 1:
				# move the editor to another splitter
				window.set_view_index( _schemeEditor, group, index )
			else:
				#if the editor is in different splitter already focus it
				window.focus_view( _schemeEditor )
			
			window.focus_view( view )
			update_view_status( view )

		else:
			# if it was us who created the other splitter close it
			if _wasSingleLayout != None:
				_wasSingleLayout.set_layout( {
					'cols': [0.0, 1.0],
					'rows': [0.0, 1.0],
					'cells': [[0, 0, 1, 1]]
				} )
			kill_scheme_editor()
			

		
		
