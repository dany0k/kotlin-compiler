@echo off

set PYTHON_HOME=C:\Users\Артём\AppData\Local\Programs\Python\Python310
set PYTHON="%PYTHON_HOME%\python.exe"

set NET_HOME=C:\Windows\Microsoft.NET\Framework64\v4.0.30319

set CSC="%NET_HOME%\csc.exe"
set ILASM="%NET_HOME%\ilasm.exe"
set ILDASM="%~dp0.\.net\x86\ildasm.exe"

set JAVA_HOME=C:\Users\Артём\.jdks\openjdk-16.0.2
set JAVA="%JAVA_HOME%\bin\java.exe"
set JAVAC="%JAVA_HOME%\bin\javac.exe"
set JAR="%JAVA_HOME%\bin\jar.exe"

set PROGUARD="%JAVA%" -jar "%~dp0\.java\proguard-assembler\lib\assembler.jar"
