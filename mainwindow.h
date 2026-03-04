#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QDragEnterEvent>
#include <QDropEvent>

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
    void on_closeButton_clicked();
    void on_grabButton_clicked();

private:
    Ui::MainWindow *ui;
};
#endif // MAINWINDOW_H
