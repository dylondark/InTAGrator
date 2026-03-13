cmake_minimum_required(VERSION 3.16)

project(InTAGrator VERSION 0.1 LANGUAGES CXX)

set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(QT NAMES Qt6 Qt5 REQUIRED COMPONENTS Widgets Network)
find_package(Qt${QT_VERSION_MAJOR} REQUIRED COMPONENTS Widgets Network)
find_package(TagLib REQUIRED)

set(PROJECT_SOURCES
        main.cpp
        mainwindow.cpp
        mainwindow.h
        mainwindow.ui
)

if(${QT_VERSION_MAJOR} GREATER_EQUAL 6)
    qt_add_executable(InTAGrator
        MANUAL_FINALIZATION
        ${PROJECT_SOURCES}
        getCoverArtUtility.h


    )
# Define target properties for Android with Qt 6 as:
#    set_property(TARGET InTAGrator APPEND PROPERTY QT_ANDROID_PACKAGE_SOURCE_DIR
#                 ${CMAKE_CURRENT_SOURCE_DIR}/android)
# For more information, see https://doc.qt.io/qt-6/qt-add-executable.html#target-creation
else()
    if(ANDROID)
        add_library(InTAGrator SHARED
            ${PROJECT_SOURCES}
        )
# Define properties for Android with Qt 5 after find_package() calls as:
#    set(ANDROID_PACKAGE_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/android")
    else()
        add_executable(InTAGrator
            ${PROJECT_SOURCES}
        )
    endif()
endif()

target_link_libraries(InTAGrator PRIVATE Qt${QT_VERSION_MAJOR}::Widgets Qt6::Network TagLib::TagLib)

# Qt for iOS sets MACOSX_BUNDLE_GUI_IDENTIFIER automatically since Qt 6.1.
# If you are developing for iOS or macOS you should consider setting an
# explicit, fixed bundle identifier manually though.
if(${QT_VERSION} VERSION_LESS 6.1.0)
  set(BUNDLE_ID_OPTION MACOSX_BUNDLE_GUI_IDENTIFIER com.example.InTAGrator)
endif()
set_target_properties(InTAGrator PROPERTIES
    ${BUNDLE_ID_OPTION}
    MACOSX_BUNDLE_BUNDLE_VERSION ${PROJECT_VERSION}
    MACOSX_BUNDLE_SHORT_VERSION_STRING ${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}
    MACOSX_BUNDLE TRUE
    WIN32_EXECUTABLE TRUE
)

# Copy songInfo.py to the build output directory at configure time
configure_file(
    ${CMAKE_SOURCE_DIR}/python_files/songInfo.py
    ${CMAKE_CURRENT_BINARY_DIR}/songInfo.py
    COPYONLY
)

# Also copy next to the executable after each build (handles multi-config generators)
add_custom_command(TARGET InTAGrator POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        ${CMAKE_SOURCE_DIR}/python_files/songInfo.py
        $<TARGET_FILE_DIR:InTAGrator>/songInfo.py
    COMMENT "Copying songInfo.py to output directory"
)

include(GNUInstallDirs)
install(TARGETS InTAGrator
    BUNDLE DESTINATION .
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

if(QT_VERSION_MAJOR EQUAL 6)
    qt_finalize_executable(InTAGrator)
endif()
