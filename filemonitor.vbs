' VBScript source code
' WMIFileEvents.vbs

Sub DoFileProcessing
        WScript.Echo "Copying " & objTargetInst.Name & " to " & strHomeFolder & "\Desktop\"
        On Error Resume Next
            fso.CopyFile objTargetInst.Name , strHomeFolder & "\Desktop\"
                WScript.Echo "file copied to " & strHomeFolder & "\Desktop\"
        On Error Resume Next
        fso.DeleteFile objTargetInst.Name
        strFilename = objTargetInst.Name
        strFilename = strHomeFolder & "\Desktop\" & Replace(LCase(strFilename), LCase(strSharePath), "")
        WScript.Echo "New file-path " & strFilename
        if InStr(LCase(strFilename), "\start.bat") > 0 Then
           On Error Resume Next
           oShell.run strFilename
           WScript.Echo "executed " & strFilename
        end if
End Sub

Set objWMIService = GetObject( "winmgmts:\\.\root\cimv2" )
Set colItems = objWMIService.ExecQuery( "Select * from Win32_ComputerSystem" )
For Each objItem in colItems
    strComputerName = objItem.Name
    WScript.Echo "Computer Name: " & strComputerName
Next

intInterval = "2"
strDrive = "z:" 
strFolder = "\\" & strComputerName & "\\"
strComputer = "." 
strSharePath = strDrive & "\" & strComputerName & "\"

Set oShell = CreateObject("WScript.Shell")
strHomeFolder = oShell.ExpandEnvironmentStrings("%USERPROFILE%")

Dim fso
Set fso = CreateObject("Scripting.FileSystemObject")

Set objWMIService = GetObject( "winmgmts:" & _ 
    "{impersonationLevel=impersonate}!\\" & _ 
    strComputer & "\root\cimv2" )

strQuery =  _
    "Select * From __InstanceOperationEvent" _
    & " Within " & intInterval _
    & " Where Targetinstance Isa 'CIM_DataFile'" _
    & " And TargetInstance.Drive='" & strDrive & "'" _
    & " And TargetInstance.Path='" & strFolder & "'"

Set colEvents = objWMIService. ExecNotificationQuery (strQuery) 

WScript.Echo "Monitoring events...from " & strDrive & strFolder
oShell.LogEvent 4, "APTC file monitoring started"

Do     
    Set objEvent = colEvents.NextEvent()
    Set objTargetInst = objEvent.TargetInstance
    
    Select Case objEvent.Path_.Class 
        
	Case "__InstanceCreationEvent" 
        WScript.Echo "Created: " & objTargetInst.Name 
	    DoFileProcessing
	Case "__InstanceDeletionEvent" 
             WScript.Echo "Deleted: " & objTargetInst.Name 
        
	Case "__InstanceModificationEvent" 
         DoFileProcessing
    End Select 
Loop