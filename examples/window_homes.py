"""Windows with homes: where a window opens, and where it goes back to.

Run it and two pins appear on the right:

    🔎  opens as a bar across the top of the code (home='top_bar')
    ⌨️  opens in the keyboard's place (home='dock'); its ⇧ button
        lifts it to a panel just above the keyboard (move_to)

Each has a 🏠 button that sends it back home (go_home). Move or resize a
window by hand and it reopens where you left it; 🏠 always goes home.
"""
import editorkit as ek

bar = ek.Window('Find bar', emoji='🔎', key='homes-bar', home='top_bar')
bar.add_page('Bar', 'A slim bar across the top of the code.')
bar.add_button('🏠', lambda window: window.go_home(), name='home')
bar.minimise()

keys = ek.Window('Keys', emoji='⌨️', key='homes-keys', home='dock')
keys.add_page('Keys', 'Opens in the keyboard place. ⇧ lifts it above the keyboard.')
keys.add_button('⇧', lambda window: window.move_to('above_dock'), name='lift')
keys.add_button('🏠', lambda window: window.go_home(), name='home')
keys.minimise()
