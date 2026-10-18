import inet.networklayer.configurator.ipv4.Ipv4NetworkConfigurator;
import inet.node.aodv.AodvRouter;
import inet.physicallayer.wireless.ieee80211.packetlevel.Ieee80211ScalarRadioMedium;
import inet.visualizer.canvas.integrated.IntegratedCanvasVisualizer;

network Konvoi
{
    parameters:
        int numCars = default(12);
        @display("bgb=15000,300");
    submodules:
        visualizer: IntegratedCanvasVisualizer {
            @display("p=100,40");
        }
        configurator: Ipv4NetworkConfigurator {
            @display("p=300,40");
        }
        radioMedium: Ieee80211ScalarRadioMedium {
            @display("p=500,40");
        }
        car[numCars]: AodvRouter;
}