#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QDragEnterEvent>
#include <QDropEvent>
#include <QProcess>

QT_BEGIN_NAMESPACE
namespace Ui {
class MainWindow;
}
QT_END_NAMESPACE

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

protected:
    void dragEnterEvent(QDragEnterEvent *event) override;
    void dropEvent(QDropEvent *event) override;

private slots:
    void on_fileInBrowseButton_clicked();
    void on_loadFileButton_clicked();
    void on_tagButton_clicked();
    void on_fileOutBrowseButton_clicked();
    void on_artBrowseButton_clicked();
    void on_grabButton_clicked();
    void onPythonProcessFinished(int exitCode, QProcess::ExitStatus exitStatus);
    void on_keepButton_clicked();
    void on_clearButton_clicked();

private:
    Ui::MainWindow *ui;
    QProcess m_pythonProcess;
    QString m_lastGrabInputFile;
};
#endif // MAINWINDOW_H
