import json
from math import sin, cos, sqrt, pi, atan, atan2, acos
from random import random

#константы и параметры
FOOD_MASS = None
GAME_HEIGHT = None
GAME_TICKS = None
GAME_WIDTH = None
INERTION_FACTOR = None
MAX_FRAGS_CNT = None
SPEED_FACTOR = None
TICKS_TIL_FUSION = None
VIRUS_RADIUS = None
VIRUS_SPLIT_MASS = None
VISCOSITY = None
FOOD_RADIUS = 2.5
SPLIT_THRESHOLD = 120
 
SCORE_FOOD = 1
SCORE_ENEMY_PART = 10
SCORE_ENEMY = 100
SCORE_VIRUS_BURST = 2

def initParams( data ):
    global FOOD_MASS, GAME_HEIGHT, GAME_TICKS, GAME_WIDTH, INERTION_FACTOR, MAX_FRAGS_CNT, \
                SPEED_FACTOR, TICKS_TIL_FUSION, VIRUS_RADIUS, VIRUS_SPLIT_MASS, VISCOSITY
    FOOD_MASS = data.get( 'FOOD_MASS' )
    GAME_HEIGHT = data.get( 'GAME_HEIGHT' )
    GAME_TICKS = data.get( 'GAME_TICKS' )
    GAME_WIDTH = data.get( 'GAME_WIDTH' )
    INERTION_FACTOR = data.get( 'INERTION_FACTOR' )
    MAX_FRAGS_CNT = data.get( 'MAX_FRAGS_CNT' )
    SPEED_FACTOR = data.get( 'SPEED_FACTOR' )
    TICKS_TIL_FUSION = data.get( 'TICKS_TIL_FUSION' )
    VIRUS_RADIUS = data.get( 'VIRUS_RADIUS' )
    VIRUS_SPLIT_MASS = data.get( 'VIRUS_SPLIT_MASS' )
    VISCOSITY = data.get( 'VISCOSITY' )

def makeCommand( x, y, debug ):
    command = {}
    command['X'] = x
    command['Y'] = y
    command['Debug'] = debug
    return command

def maxTurnAngle( M, VX, VY ):
    a = INERTION_FACTOR / M
    V = sqrt( VX ** 2 + VY ** 2 )
    Vmax = SPEED_FACTOR / sqrt( M )
    # если скорость нуменьше пороговой - то можем развернуться в любои напрвалении
    if V == 0 or V <= ( a * Vmax / ( 1 - a ) ):
        return pi, pi
    #проекции направления приложения силы на исходную скорость при максимальном повороте
    nx = -a * Vmax / ( ( 1 - a ) * V ) 
    ny = sqrt( 1 - nx ** 2 ) 
    Vxnext = V * ( 1 - a ) + a * Vmax * nx
    Vynext = a * Vmax * ny
    return atan2( Vynext, Vxnext ), atan2( ny, nx )  
    
def distance( a, b ):
    return sqrt( ( a.X - b.X ) ** 2 + ( a.Y - b.Y ) ** 2 )

def normalize( x, y ):
    l = sqrt( x ** 2 + y ** 2 )
    if l == 0:
        return x, y
    else:
        return x / l, y / l

class GameObject:
    def __init__( self, data ):
        self.X = data.get( 'X' )
        self.Y = data.get( 'Y' )
    
    def distance( self, other ):
        return distance( self, other )
    
class Virus( GameObject ):
    def __init__( self, data ):
        super().__init__( data )
        self.Id = data.get( 'Id' )
        self.M = data.get( 'M' )
    
class PlayerPart( Virus ):
    def __init__( self, data ):
        super().__init__( data )
        self.R = data.get( 'R' )
        self.VX = 0
        self.VY = 0
    
    # максимальная скорость игрока
    def maxSpeed( self ):
        return SPEED_FACTOR / sqrt( self.M )    
        
class MinePart( PlayerPart ):
    def __init__( self, data ):
        super().__init__( data )
        self.VX = data.get( 'SX' )
        self.VY = data.get( 'SY' )
        self.V = sqrt( self.VX ** 2 + self.VY ** 2 )
        self.vx, self.vy = normalize( self.VX, self.VY )
        # таймер слияния - может отсутствовать
        if 'TTF' in data:
            self.TTF = data.get( 'TTF' ) 
        else:
            self.TTF = 0
        self.MaxSpeed = self.maxSpeed()
        self.Speed = sqrt( self.VX ** 2 + self.VY ** 2 )
        self.MaxTurnAngle, _ = maxTurnAngle( self.M, self.VX, self.VY )
        # параметры наблюдаемой данным куском области
        self.ObservationX = self.X + self.vx * 10
        self.ObservationY = self.Y + self.vy * 10
        self.ObservationR = None # радиус зависит от общего кол-ва частей - устанавливается стратегией
        
    def isPointVisible( self, X, Y ):
        return sqrt( ( self.ObservationX - X ) ** 2 + ( self.ObservationY - Y ) ** 2 ) <= self.ObservationR
        
    def distanceToBorder( self ):
        return min( [self.X - self.R, GAME_WIDTH - self.X - self.R, self.Y - self.R, GAME_HEIGHT - self.Y - self.R ] )
    
    def borderStandoff( self ):
        minDistance = self.R + 100.0
        nx = 0.0
        ny = 0.0
        if self.X < minDistance:
            nx = 10.0 / ( 2 + self.X )
        elif self.X > GAME_WIDTH - minDistance:
            nx = -10.0 / ( 2 + GAME_WIDTH - self.X )
        if self.Y < minDistance:
            ny = 10.0 / ( 2 + self.Y )
        elif self.Y > GAME_HEIGHT - minDistance:
            ny = -10.0 / ( 2 + GAME_HEIGHT - self.Y )
        if nx != 0 or ny != 0:
            nx, ny = normalize( nx, ny )
        return nx, ny
    
    def borderStandoffFree( self ):
        xmin, ymin = self.getBorderMargin()
        nx = 0
        ny = 0
        if self.X < xmin:
            nx = 1
        elif self.X > GAME_WIDTH - xmin:
            nx = -1
        if self.Y < ymin:
            ny = 1
        elif self.Y > GAME_HEIGHT - ymin:
            ny = -1
        if nx == 0 and ny != 0:
            if self.X - self.R < 2:
                nx = 1
            elif self.X + self.R > GAME_WIDTH - 2:
                nx = -1
        elif nx != 0 and ny == 0:
            if self.Y - self.R < 2:
                ny = 1
            elif self.Y + self.R > GAME_HEIGHT - 2:
                ny = -1
        if nx != 0 or ny != 0:
            nx, ny = normalize( nx, ny )
        return nx, ny
    
    # вычисление направления приложения силы для максимального поворота к заданной точке
    def getTurnAngleToTarget( self, X0, Y0, Vx, Vy, Xt, Yt ):
        # угол к точке
        angle = atan2( Yt - Y0, Xt - X0 )
        if Vx == 0 and Vy == 0:
            # если скорость нулевая - сразу движемся в направлении цели
            return angle
        # вычисляем угол относительно совего направления
        a = INERTION_FACTOR / self.M
        V = sqrt( Vx ** 2 + Vy ** 2 )
        Vmax = self.MaxSpeed
        # направление скорости
        selfAngle = atan2( Vy, Vx )
        # угол между скоростью и направлением на точку
        angle -= selfAngle
        nxmax = a * Vmax / ( (1 - a) * V )
        cosAngle = cos( angle )
        # выбираем угол, который даст максимальную скорость
        nx1 = ( cosAngle ** 2 - 1 + cosAngle * sqrt( nxmax ** 2 + cosAngle ** 2 - 1 ) ) / nxmax
        if angle >= 0:
            ny1 = sqrt( 1 - nx1 ** 2 )
        else:
            ny1 = -sqrt( 1 - nx1 ** 2 )
        vx1 = ( 1 - a ) * V + a * nx1 * Vmax
        vy1 = a * ny1 * Vmax
        v1 = sqrt( vx1 ** 2 + vy1 ** 2 )
        nx2 = ( cosAngle ** 2 - 1 - cosAngle * sqrt( nxmax ** 2 + cosAngle ** 2 - 1 ) ) / nxmax
        if angle >= 0:
            ny2 = sqrt( 1 - nx2 ** 2 )
        else:
            ny2 = -sqrt( 1 - nx2 ** 2 )
        vx2 = ( 1 - a ) * V + a * nx2 * Vmax
        vy2 = a * ny2 * Vmax
        v2 = sqrt( vx2 ** 2 + vy2 ** 2 )
        if v1 >= v2:
            return atan2( ny1, nx1 ) + selfAngle
        else:
            return atan2( ny2, nx2 ) + selfAngle
    
    # оценка времени достижения заданного объекта с полным перекрытием его
    # при использовании поворотов на максимальный возможный угол
    # оценка времени достижения заданного объекта с полным перекрытием его
    def getTimeToTarget( self, X, Y, R, bestTime ):
        captureDistance = self.R - R
        T = 0
        X0 = self.X
        Y0 = self.Y
        Vx0 = self.VX
        Vy0 = self.VY
        curDistance = sqrt( (self.X - X)**2 + (self.Y - Y)**2 )
        prevDistance = curDistance
        while curDistance > captureDistance and T < 100:
            targetAngleSize = atan( captureDistance / curDistance )
            X0, Y0, Vx0, Vy0, curDistance = self.stepToTarget( X0, Y0, Vx0, Vy0, X, Y, targetAngleSize )
            if prevDistance < curDistance:
                return GAME_TICKS
            prevDistance = curDistance
            T += 1
            # обрезаем поиск ,если уже найдена еда до которой можно добраться быстрее
            if T >= bestTime:
                return GAME_TICKS
        return T
        
    def stepToTarget( self, X0, Y0, Vx0, Vy0, Xt, Yt, targetAngleSize ):
        t = self.getBestDirectionToTarget( X0, Y0, Vx0, Vy0, Xt, Yt, targetAngleSize )
        Vmax = self.MaxSpeed
        a = INERTION_FACTOR / self.M
        Vx1 = (1 - a)*Vx0 + a * Vmax * cos(t)
        Vy1 = (1 - a)*Vy0 + a * Vmax * sin(t)
        X1 = X0 + Vx1
        Y1 = Y0 + Vy1
        return X1, Y1, Vx1, Vy1, sqrt( (X1 - Xt)**2 + (Y1 - Yt)**2  )
    
    # направление приложения силы для максимального уменьшения угла до цели
    def getBestDirectionToTarget( self, X0, Y0, Vx0, Vy0, Xt, Yt, targetAngleSize ):
        # угол от нас до цели
        angle = atan2( Yt - Y0, Xt - X0 )
        Vx = Vx0
        Vy = Vy0
        # угол нашей скорости
        direction = atan2( Vy, Vx )
        # цгол между нашей скоростью и целью
        deltaAngle = angle - direction
        # если цель попдает в створ - прсото едем вперед
        if abs(deltaAngle) < targetAngleSize:
            return direction
        turnAngle = 0
        maxAngle, turnDirection = maxTurnAngle( self.M, Vx, Vy )
        if abs(deltaAngle) < maxAngle:
            # если можем доврнуть на цель то доворачиваем
            turnAngle = self.getTurnAngleToTarget( X0, Y0, Vx, Vy, Xt, Yt  )
        else:
            # если цель находится за допустимымы пределами - доворачиваем на максимальный угол
            if deltaAngle >= 0:
                turnAngle = turnDirection + direction
            else:
                turnAngle = -turnDirection + direction
        return turnAngle    
    
    # направление приложения силы для максимального отдаления от цели
    def getBestDirectionFromTarget( self, X0, Y0, Vx0, Vy0, Xt, Yt ):
        # координаты цели относительно нас
        X = Xt - X0
        Y = Yt - Y0
        Vx = Vx0
        Vy = Vy0
        V = sqrt( Vx ** 2 + Vy ** 2 )
        L = sqrt( X ** 2 + Y ** 2 )
        a = INERTION_FACTOR / self.M
        Vmax = SPEED_FACTOR / sqrt( self.M )
        # экстремальные углы
        k1 = sqrt( (a - 1)**2 * V * V + 2 * ( a - 1 ) * ( X * Vx + Y * Vy ) + L ** 2 )
        k2 = (1 - a) * Vx - X
        k3 = Y - (1 - a) * Vy
        t1 = 2 * atan( ( k1 + k2 ) / k3 )
        t2 = -2 * atan( ( k1 - k2 ) / k3 )
        # результаты для первого угла
        X1 = (1 - a)*Vx + a * Vmax * cos(t1)
        Y1 = (1 - a)*Vy + a * Vmax * sin(t1)
        L1 = sqrt( ( X - X1 ) ** 2 + ( Y - Y1 ) ** 2 )
        # результаты для второго угла
        X2 = (1 - a)*Vx + a * Vmax * cos(t2)
        Y2 = (1 - a)*Vy + a * Vmax * sin(t2)
        L2 = sqrt( ( X - X2 ) ** 2 + ( Y - Y2 ) ** 2 )
        tmax = t1 # угол приложения силы, который приведет к максимальному удалению от цели
        if L1 < L2:
            tmax = t2
        return tmax
    
    # вычисляем минимально расстояние от границы, на котором мы сможем затормозить
    # если тормозить будем относительно одной границы под углом 45 градусов
    def getBorderMargin( self ):
        Lx = 0
        Ly = 0
        a = INERTION_FACTOR / self.M
        Vmax = SPEED_FACTOR / ( sqrt( self.M ) * sqrt(2.0) )
        Vx = abs( self.VX )
        Vy = abs( self.VY )
        while Vx > 0 or Vy > 0:
            Vx = (1 - a) * Vx - a * Vmax
            Vy = (1 - a) * Vy - a * Vmax
            if Vx > 0:
                Lx += Vx
            if Vy > 0:
                Ly += Vy
        return ( Lx + self.R ) * 2, ( Ly + self.R ) * 2
            
class Food( GameObject ):
    def __init__( self, data ):
        super().__init__( data )
        self.R = FOOD_RADIUS

class Ejection( GameObject ):
    def __init__( self, data ):
        super().__init__( data )
        self.pId = data.get( 'pId' )
    
class Strategy:
    
    def __init__( self ):
        self.mine = []
        self.direction = None
        self.food = [] # актуальная еда
        self.visibleFood = set()
        self.ejection = []
        self.virus = []
        self.player = []
        self.dangerous = []
        self.eatable = []
        self.fieldDiameter = None
        self.minSelfRadius = None
        self.left = None
        self.right = None
        self.top = None
        self.bottom = None
        self.isSplittable = False
        self.runPoint = None #точка отступление
        self.totalMass = 0
        self.timeFromLastContact = 1000 #время с момента последнего наблюдения противника
        self.corners = [] # углы карты - не рекомендуется убегать в угол
        self.prevCoords = {} # координаты противников на предидущем ходу
        self.runCount = 0 # оставшееся время убегания - после пропадания охотника
        self.dXrun = None # направление убегания
        self.dYrun = None
        self.runOutPart = None # часть которая убегает
        # старая запомненная - ключ - ключ коодинаты, значение - тик последнего наблюдения
        # слишком старые записи будем выбрасывать
        self.memorizedFood = {} 
        self.tickCount = 0
        
    def parseData( self, data ):
        mine, objects = data.get( 'Mine' ), data.get( 'Objects' )
        self.mine.clear()
        self.minSelfRadius = sqrt( GAME_HEIGHT ** 2 + GAME_WIDTH ** 2 )
        self.left = GAME_WIDTH
        self.right = 0
        self.top = GAME_HEIGHT
        self.bottom = 0
        self.isSplittable = False
        minMass = 10000.0
        self.totalMass = 0
        
        for m in mine:
            self.mine.append( MinePart( m ) )
        for m in self.mine:
            self.minSelfRadius = min( self.minSelfRadius, m.R )
            self.left = min( self.left, m.X - m.R )
            self.right = max( self.right, m.X + m.R )
            self.top = min( self.top, m.Y - m.R )
            self.bottom = max( self.bottom, m.Y + m.R )
            if m.M >= SPLIT_THRESHOLD:
                self.isSplittable = True
            if m.M < minMass:
                minMass = m.M
            self.totalMass += m.M
            # вычисляем радиус обзора
            partsCount = len( self.mine )
            if partsCount == 1:
                m.ObservationR = m.R * 4
            else:
                m.ObservationR = m.R * 2.5 * sqrt( partsCount )
        self.food.clear()
        self.visibleFood.clear()
        self.ejection.clear()
        self.virus.clear()
        self.player.clear()
        self.dangerous.clear()
        self.eatable.clear()
        for o in objects:
            objectType = o.get( 'T' )
            if objectType == 'F':
                food = Food( o )
                if self.isFoodReachable( food ):
                    self.food.append( food )
                    self.visibleFood.add( (food.X, food.Y) )
            elif objectType == 'E':
                self.ejection.append( Ejection( o ) )
            elif objectType == 'V':
                self.virus.append( Virus( o ) )
            elif objectType == 'P':
                p = PlayerPart( o )
                if p.Id in self.prevCoords:
                    prevCoords = self.prevCoords[p.Id]
                    p.VX = p.X - prevCoords[0]
                    p.VY = p.Y - prevCoords[1]
                if minMass * 1.2 < p.M:
                    self.dangerous.append( p )
                elif self.isEatable( p ):
                    self.eatable.append( p )
                self.player.append( p )
        if len( self.dangerous ) > 0 or len( self.eatable ) > 0 or len( self.player ) > 0:
            self.timeFromLastContact = 0
        else:
            self.timeFromLastContact += 1
        self.prevCoords.clear()
        for p in self.dangerous:
            self.prevCoords[p.Id] = [ p.X, p.Y ]
        for p in self.eatable:
            self.prevCoords[p.Id] = [ p.X, p.Y ]
        for p in self.player:
            self.prevCoords[p.Id] = [ p.X, p.Y ]
        self.processFood()
            
    def processFood( self ):
        # добавить новую еду или обновить время у старой
        toDelete = []
        if len( self.mine ) > 4:
            self.memorizedFood.clear()
            return
        for f in self.memorizedFood:
            if self.isPointVisible( f[0], f[1] ) and not( f in self.visibleFood ):
                # выбросить еду которая уже должна быть видима, но не наблюдается
                toDelete.append( f )
            elif self.tickCount - self.memorizedFood[f] > 50: # запоминаем еду на 50 ходов
                # выбросить слишком старые данные
                toDelete.append( f )
        for f in toDelete:
            del self.memorizedFood[f]
        for f in self.visibleFood:
            self.memorizedFood[f] = self.tickCount
            
    def isPointVisible( self, X, Y ):
        for m in self.mine:
            if m.isPointVisible( X, Y ):
                return True
        return False
            
    def run( self ):
        initParams( json.loads( input() ) )
        self.fieldDiameter = sqrt( GAME_WIDTH ** 2 + GAME_HEIGHT ** 2 )
        while True:
            self.tickCount += 1
            data = json.loads( input() )
            cmd = self.on_tick( data )
            print( json.dumps(cmd) )

    # определяем интерес к куску противника
    def isEatable( self, player ):
        # ближайшая к игроку наша часть больше него по массе
        minDist = None
        nearest = None
        for m in self.mine:
            if nearest is None:
                nearest = m
                minDist = m.distance( player )
            else:
                curDist = m.distance( player )
                if curDist < minDist:
                    nearest = m
                    minDist = curDist
        player.Nearest = nearest
        player.Distance = minDist
        if player.M * 1.2 >= nearest.M:
            return False
        # направление от игрока на нас
        dx, dy = normalize( nearest.X - player.X, nearest.Y - player.Y )
        vx = player.VX
        vy = player.VY
        v = sqrt( vx ** 2 + vy ** 2 )
        if v == 0:
            return True
        vx, vy = normalize( vx, vy )
        dotProduct = dx * vx + dy * vy
        return dotProduct >= 0 or v < SPEED_FACTOR / ( 2 * sqrt(nearest.M) )
        
    def isFoodReachable( self, food ):
        effectiveRadius = self.minSelfRadius - FOOD_RADIUS / 6
        # для угла (0, 0)
        if food.X < self.minSelfRadius and food.Y < self.minSelfRadius:
            checkPoint = GameObject( { 'X': self.minSelfRadius, 'Y': self.minSelfRadius } )
            return distance( checkPoint, food ) < effectiveRadius
        elif food.X > GAME_WIDTH - self.minSelfRadius and food.Y < self.minSelfRadius:
            checkPoint = GameObject( { 'X': GAME_WIDTH - self.minSelfRadius, 'Y': self.minSelfRadius } )
            return distance( checkPoint, food ) < effectiveRadius
        elif food.X < self.minSelfRadius and food.Y > GAME_HEIGHT - self.minSelfRadius:
            checkPoint = GameObject( { 'X': self.minSelfRadius, 'Y': GAME_HEIGHT - self.minSelfRadius } )
            return distance( checkPoint, food ) < effectiveRadius
        elif food.X > GAME_WIDTH - self.minSelfRadius and food.Y > GAME_HEIGHT - self.minSelfRadius:
            checkPoint = GameObject( { 'X': GAME_WIDTH - self.minSelfRadius, 'Y': GAME_HEIGHT - self.minSelfRadius } )
            return distance( checkPoint, food ) < effectiveRadius
        else:
            return food.X > ( FOOD_RADIUS / 6 ) and food.X < ( GAME_WIDTH - FOOD_RADIUS / 6 ) and food.Y > ( FOOD_RADIUS / 6 ) and food.Y < ( GAME_HEIGHT - FOOD_RADIUS / 6 )
        
    # ищем минимальное расстояние между своими частями и заданным объектом
    def distance( self, obj ):
        return min( map( (lambda x: x.distance( obj ) ), self.mine ) )
            
    # ищем единичный вектор отталкивания от границ
    # от границ отталкиваемся по нормали 
    def getBorderStandoff( self ):
        dx = 0
        dy = 0
        dMin = 1000000
        for m in self.mine:
            d = m.distanceToBorder()
            if d < dMin:
                dx, dy = m.borderStandoff()
                dMin = d
        return dx, dy
    
    def getBorderStandoffFree( self ):
        dx = 0
        dy = 0
        dMin = 1000000
        for m in self.mine:
            d = m.distanceToBorder()
            if d < dMin:
                dx, dy = m.borderStandoffFree()
                dMin = d
        return dx, dy
    
    def currentSpeed( self ):
        VX = 0
        VY = 0
        for m in self.mine:
            VX += m.VX * m.M
            VY += m.VY * m.M
        VX /= self.totalMass
        VY /= self.totalMass
        return VX, VY
    
    def setPointOnBorder( self, pt, nx, ny ):
        # ищем границу, которую пересекаем раньше всего
        x = pt.X
        y = pt.Y
        Lmin = 10000
        l = []
        if nx != 0:
            l.append( -x/nx )
            l.append( (GAME_WIDTH - x)/nx )
        if ny != 0:
            l.append( -y/ny )
            l.append( (GAME_HEIGHT-y)/ny )
        l.sort()
        for curLen in l:
            if curLen > 0 and curLen < Lmin:
                Lmin = curLen
        return x + nx * Lmin, y + ny * Lmin

    def distanceToBorder( self ):
        return min( map( lambda x: x.distanceToBorder(), self.mine ) )
        
    # ищем пару опасный противник - своя часть с минимальным расстоянием
    # убегать будем по направлени, соединяющему центры этой пары
    # если можем слиться
    def runOut( self ):
        minDistance = 10000
        mineEnd = None
        enemyEnd = None
        for mine in self.mine:
            for enemy in self.dangerous:
                distance = mine.distance( enemy )
                if minDistance > distance:
                    mineEnd = mine
                    enemyEnd = enemy
                    minDistance = distance
        self.runOutPart = mineEnd
        dx = mineEnd.X - enemyEnd.X
        dy = mineEnd.Y - enemyEnd.Y
        dx, dy = normalize( dx, dy )
        self.runXd = dx
        self.runYd = dy 
        self.runCount = 50
        # вектор отталкивания от границ
        sx, sy = self.getBorderStandoff()
        dx += sx
        dy += sy
        dx, dy = normalize( dx, dy )
        dx, dy = self.setPointOnBorder( mineEnd, dx, dy )
        command = makeCommand( dx, dy, 'run out' )
        if self.isSplittable:
            command['Split'] = True
        return command
    
    def runByDirection( self ):
        if self.distanceToBorder() < 2:
            self.runCount = 0
            return self.makeFreeMove()
        self.runCount -= 1
        dx = self.runXd
        dy = self.runYd
        mine = self.runOutPart
        dx, dy = self.setPointOnBorder( mine, dx, dy )
        command = makeCommand( dx, dy, 'continue run out' )
        if self.isSplittable:
            command['Split'] = True
        return command
    
    def getSelfMinMass( self ):
        return min( map( lambda x: x.M, self.mine ) )
    
    def getOtherMaxMass( self ):
        return max( map( lambda x: x.M, self.player ) )
    
    # при атаке разрешаем делиться если половина нашей самолей легков части на 20% тяжелее любой атакуемой части
    # если наша скорость направленна на противника
    def attack( self ):
        minDistance = 10000
        target = None
        # выбираем ближайшего среди съедобных
        for enemy in self.eatable:
            if target is None or minDistance > enemy.Distance:
                target = enemy
                minDistance = enemy.Distance
        mine = target.Nearest
        # минимальное время до жертвы
        timeToTarget = target.Distance / mine.MaxSpeed
        x = target.X + target.VX * timeToTarget
        y = target.Y + target.VY * timeToTarget
        targetAngleSize = atan( ( mine.R - target.R ) / target.Distance )
        t = mine.getBestDirectionToTarget( mine.X, mine.Y, mine.VX, mine.VY, x, y, targetAngleSize )
        dx = cos(t)
        dy = sin(t)
        x, y = self.setPointOnBorder( mine, dx, dy )
        command = makeCommand( x, y, 'attack' )
        
        if self.getSelfMinMass() >= self.getOtherMaxMass() * 1.2 and self.isSplittable:
            command['Split'] = True
        return command
    
    def moveToFood( self ):
        minTime = GAME_TICKS
        bestFood = None
        bestMine = None
        for m in self.mine:
            for f in self.visibleFood:
                t = m.getTimeToTarget( f[0], f[1], 1, minTime )
                if t < minTime:
                    bestMine = m
                    bestFood = f
                    minTime = t
            for f in self.memorizedFood:
                t = m.getTimeToTarget( f[0], f[1], 1, minTime )
                if t < minTime:
                    bestMine = m
                    bestFood = f
                    minTime = t
        if minTime >= GAME_TICKS:
            return self.makeFreeMove()
        bestFood = Food( { 'X': bestFood[0], 'Y': bestFood[1] } )
        distance = bestMine.distance( bestFood )
        targetAngleSize = atan( ( bestMine.R - bestFood.R ) / distance )
        t = bestMine.getBestDirectionToTarget( bestMine.X, bestMine.Y, bestMine.VX, bestMine.VY, bestFood.X, bestFood.Y, targetAngleSize )
        nx = cos(t)
        ny = sin(t)
        x, y = self.setPointOnBorder( bestMine, nx, ny )
        return makeCommand( x, y, 'to food' )
    
    def makeFreeMove( self ):
        # движемся в заданном напралении
        # в свободном состоянии движемся по напралению скорости, если она есть
        VX, VY = self.currentSpeed()
        if VX == 0 and VY == 0:
            angle = 2 * pi * random()
            VX = cos( angle )
            VY = sin( angle )
        VX, VY = normalize( VX, VY )
        dx, dy = self.getBorderStandoffFree()
        if dx != 0 or dy != 0:
            VX += dx
            VY += dy
            VX, VY = normalize( VX, VY )
        x, y = self.setPointOnBorder( self.mine[0], VX, VY )
        return makeCommand( x, y, 'free move' )
    
    def on_tick( self, data ):
        self.parseData( data )
        command = {}
        if len( self.mine ) == 0:
            command = makeCommand( 0, 0, 'game over' )
        else:
            if len( self.dangerous ) > 0:
                #избегаем опасных соседей
                command = self.runOut()
            elif len( self.eatable ) > 0:
                # пытаемся съесть конкурента если можем, преследовать нужно с упреждением
                # но не пытаемся догнать, то, что догнать нельзя
                command = self.attack()
            elif self.runCount > 0:
                # если начали от кого-то убегать - продолжаем, пока не обнулится счетчик
                command = self.runByDirection()
            else:
                if len( self.food ) > 0 or len( self.memorizedFood ) > 0:
                    # пытаемся съесть еду если видно
                    command = self.moveToFood()
                else:
                    command = self.makeFreeMove()
                if self.isSplittable and self.timeFromLastContact > 50:
                    command['Split'] = True
        # нужно скорректировать для случая близости к границе
        return command

if __name__ == '__main__':
    s = Strategy()
    s.run()