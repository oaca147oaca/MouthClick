Option Explicit
Dim shell, files, folder
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
shell.Run "wscript.exe " & Chr(34) & folder & "\Abrir MouthClick.vbs" & Chr(34) & " --config", 0, False
