:: More on nvcc
:: nvcc == CUDA compiler
:: -arch=sm_XX ==> XX = the compute compability of the NVIDIA card (see https://developer.nvidia.com/cuda-gpus)
:: Exemple : 	GTX950M ==> compute capability 5.0 ==> -arch=sm_50
::		RTX3060 ==> compute capability 8.6 ==> -arch=sm_86
:: -ccbin == the c compiler that nvcc use (put the acess for the default cl.exe on VS studio, can be subject to change, for exemple if another version is installed)
:: -o FILENAME == like with gcc, the executable will be name FILENAME(.exe)
:: Then, the main cu file
nvcc -arch=sm_50 -ccbin="C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.42.34433\bin\Hostx64\x64\cl.exe" -o "2048 but with a twist" main.cu