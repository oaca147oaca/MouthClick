Option Explicit
Dim shell, files, folder, command
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = folder
command = "py -3.11 " & Chr(34) & folder & "\iniciar_mouthclick.pyw" & Chr(34)
If WScript.Arguments.Count > 0 Then
    If WScript.Arguments(0) = "--config" Then command = command & " --config"
End If
On Error Resume Next
shell.Run command, 0, False
If Err.Number <> 0 Then
    MsgBox "No se pudo iniciar MouthClick. Revisa que Python 3.11 este instalado.", 16, "MouthClick"
End If
